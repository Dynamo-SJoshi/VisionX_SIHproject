# File: src/tracker/track.py
import math
import logging
from collections import deque, Counter
from typing import List, Dict, Tuple, Optional
import numpy as np

from src.schemas.detection import BoundingBox, Detection
from src.schemas.track import Track

logger = logging.getLogger(__name__)


def compute_iou(boxA: BoundingBox, boxB: BoundingBox) -> float:
    """Computes Intersection over Union (IoU) between two bounding boxes."""
    xA = max(boxA.x1, boxB.x1)
    yA = max(boxA.y1, boxB.y1)
    xB = min(boxA.x2, boxB.x2)
    yB = min(boxA.y2, boxB.y2)

    inter_w = max(0.0, xB - xA)
    inter_h = max(0.0, yB - yA)
    inter_area = inter_w * inter_h

    areaA = boxA.area
    areaB = boxB.area
    union_area = areaA + areaB - inter_area

    if union_area <= 0:
        return 0.0
    return inter_area / union_area


def compute_center_distance(boxA: BoundingBox, boxB: BoundingBox) -> float:
    """Computes Euclidean pixel distance between the centers of two boxes."""
    c1 = boxA.center
    c2 = boxB.center
    return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)


class SingleTrackState:
    """
    Internal state for an individual tracked object.
    Includes temporal class majority voting to prevent label flickering.
    """

    def __init__(self, track_id: int, detection: Detection, history_len: int = 20):
        self.track_id = track_id
        self.class_history: deque = deque(maxlen=history_len)
        self.class_history.append(detection.class_name)
        self.class_name = detection.class_name

        self.bbox = detection.bbox
        self.confidence = detection.confidence
        self.velocity = (0.0, 0.0)
        self.age = 1
        self.hits = 1
        self.time_since_update = 0
        self.prev_center = detection.bbox.center

    def update(self, detection: Detection) -> None:
        """Updates track with matching detection and applies class voting."""
        curr_center = detection.bbox.center
        dx = curr_center[0] - self.prev_center[0]
        dy = curr_center[1] - self.prev_center[1]
        self.velocity = (round(dx, 2), round(dy, 2))
        self.prev_center = curr_center

        self.bbox = detection.bbox
        self.confidence = detection.confidence

        # Temporal Majority Voting: Keeps class stable across frame flickers
        self.class_history.append(detection.class_name)
        most_common_class, _ = Counter(self.class_history).most_common(1)[0]
        self.class_name = most_common_class

        self.hits += 1
        self.age += 1
        self.time_since_update = 0

    def mark_missed(self) -> None:
        """Marks track as unobserved in current frame."""
        self.time_since_update += 1
        self.age += 1
        self.velocity = (0.0, 0.0)

    def to_schema(self) -> Track:
        """Converts internal track state to public Pydantic Track schema."""
        return Track(
            track_id=self.track_id,
            class_name=self.class_name,
            bbox=self.bbox,
            confidence=self.confidence,
            velocity=self.velocity,
            age=self.age,
            hits=self.hits
        )


class ObjectTracker:
    """
    Real-time persistent multi-object tracker for on-board experiment objects.
    Features robust association across fast hand movements and temporal class smoothing.
    """

    def __init__(
        self,
        iou_threshold: float = 0.10,
        max_center_distance: float = 250.0,
        max_lost_frames: int = 20,
        min_hits: int = 1
    ):
        self.iou_threshold = iou_threshold
        self.max_center_distance = max_center_distance
        self.max_lost_frames = max_lost_frames
        self.min_hits = min_hits
        self.next_id = 1
        self.active_tracks: Dict[int, SingleTrackState] = {}

    def update(self, detections: List[Detection]) -> List[Track]:
        """
        Updates tracker state with new frame detections while supporting multiple simultaneous objects.

        Args:
            detections: List of Detection objects from YOLO detector.

        Returns:
            List of active Track objects with persistent track IDs.
        """
        unmatched_dets = list(range(len(detections)))
        unmatched_tracks = list(self.active_tracks.keys())
        matches: List[Tuple[int, int]] = []

        # Stage 1: IoU Association
        if self.active_tracks and detections:
            track_ids = list(self.active_tracks.keys())
            iou_matrix = np.zeros((len(track_ids), len(detections)), dtype=np.float32)

            for i, tid in enumerate(track_ids):
                for j, det in enumerate(detections):
                    # Higher affinity for identical class
                    class_factor = 1.0 if self.active_tracks[tid].class_name == det.class_name else 0.6
                    iou_matrix[i, j] = compute_iou(self.active_tracks[tid].bbox, det.bbox) * class_factor

            while True:
                if iou_matrix.size == 0 or np.max(iou_matrix) < self.iou_threshold:
                    break
                max_idx = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
                i, j = int(max_idx[0]), int(max_idx[1])
                t_id = track_ids[i]

                matches.append((t_id, j))
                if t_id in unmatched_tracks:
                    unmatched_tracks.remove(t_id)
                if j in unmatched_dets:
                    unmatched_dets.remove(j)

                iou_matrix[i, :] = -1.0
                iou_matrix[:, j] = -1.0

        # Stage 2: Proximity Fallback Association for fast moving items
        if unmatched_tracks and unmatched_dets:
            for t_id in list(unmatched_tracks):
                track = self.active_tracks[t_id]
                best_dist = float("inf")
                best_d_idx = None

                for d_idx in unmatched_dets:
                    det = detections[d_idx]
                    dist = compute_center_distance(track.bbox, det.bbox)
                    # Check distance limit
                    if dist < self.max_center_distance and dist < best_dist:
                        best_dist = dist
                        best_d_idx = d_idx

                if best_d_idx is not None:
                    matches.append((t_id, best_d_idx))
                    unmatched_tracks.remove(t_id)
                    unmatched_dets.remove(best_d_idx)

        # Update matched tracks
        for t_id, d_idx in matches:
            self.active_tracks[t_id].update(detections[d_idx])

        # Mark unmatched tracks as missed
        for t_id in unmatched_tracks:
            self.active_tracks[t_id].mark_missed()

        # Create new tracks for unmatched detections
        for d_idx in unmatched_dets:
            det = detections[d_idx]
            new_track = SingleTrackState(self.next_id, det)
            self.active_tracks[self.next_id] = new_track
            self.next_id += 1

        # Clean up dead tracks exceeding max_lost_frames
        dead_ids = [
            tid for tid, track in self.active_tracks.items()
            if track.time_since_update > self.max_lost_frames
        ]
        for tid in dead_ids:
            del self.active_tracks[tid]

        # Return active tracks (including recently seen tracks to prevent flicker)
        return [
            track.to_schema()
            for track in self.active_tracks.values()
            if track.hits >= self.min_hits and track.time_since_update <= 1
        ]

    def reset(self) -> None:
        """Resets tracker state."""
        self.next_id = 1
        self.active_tracks.clear()
