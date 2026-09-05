"""
Object and Person Tracking Implementation for BAS-HAR Assistant.

Provides:
- Centroid / IOU spatial tracking across consecutive video frames
- Stable Track IDs for astronauts and scientific instruments/payload objects
- Track trajectory history and velocity estimation
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple
import numpy as np

from src.interfaces.tracker import TrackerInterface
from src.schemas.common import BBox, utc_now
from src.schemas.detection import Detection
from src.schemas.track import Track

logger = logging.getLogger(__name__)


def compute_iou(boxA: BBox, boxB: BBox) -> float:
    """Computes Intersection Over Union (IOU) between two bounding boxes (x1, y1, x2, y2)."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0:
        return 0.0

    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    unionArea = float(boxAArea + boxBArea - interArea)
    if unionArea <= 0:
        return 0.0

    return interArea / unionArea


class EntityTracker(TrackerInterface):
    """
    Real-time spatial tracker maintaining stable track IDs across frames for BAS-HAR.
    """

    def __init__(self, iou_threshold: float = 0.25, max_lost_frames: int = 15) -> None:
        self.iou_threshold = iou_threshold
        self.max_lost_frames = max_lost_frames
        self._next_track_id = 1
        self._active_tracks: Dict[int, Track] = {}
        self._lost_frame_counts: Dict[int, int] = {}

    def update(self, detections: List[Detection]) -> List[Track]:
        """
        Associates frame detections to existing tracks or assigns new track IDs.
        """
        if not detections:
            # Increment lost counter for all existing tracks
            for tid in list(self._active_tracks.keys()):
                self._lost_frame_counts[tid] = self._lost_frame_counts.get(tid, 0) + 1
                if self._lost_frame_counts[tid] > self.max_lost_frames:
                    del self._active_tracks[tid]
                    del self._lost_frame_counts[tid]
            return list(self._active_tracks.values())

        matched_tracks: List[Track] = []
        unmatched_dets = list(range(len(detections)))
        unmatched_tracks = list(self._active_tracks.keys())

        # Match existing tracks with detections via IOU and label match
        for tid in unmatched_tracks:
            track = self._active_tracks[tid]
            best_iou = 0.0
            best_det_idx = -1

            for det_idx in unmatched_dets:
                det = detections[det_idx]
                if det.label == track.label:
                    iou = compute_iou(track.bbox, det.bbox)
                    if iou > best_iou:
                        best_iou = iou
                        best_det_idx = det_idx

            if best_iou >= self.iou_threshold and best_det_idx >= 0:
                det = detections[best_det_idx]
                updated_track = Track(
                    track_id=tid,
                    label=det.label,
                    bbox=det.bbox,
                    confidence=det.confidence,
                    frame_id=det.frame_id,
                    timestamp=utc_now(),
                    age_frames=track.age_frames + 1,
                    is_confirmed=True,
                )
                self._active_tracks[tid] = updated_track
                self._lost_frame_counts[tid] = 0
                matched_tracks.append(updated_track)
                unmatched_dets.remove(best_det_idx)
            else:
                self._lost_frame_counts[tid] = self._lost_frame_counts.get(tid, 0) + 1
                if self._lost_frame_counts[tid] <= self.max_lost_frames:
                    matched_tracks.append(track)
                else:
                    del self._active_tracks[tid]
                    del self._lost_frame_counts[tid]

        # Register new tracks for remaining detections
        for det_idx in unmatched_dets:
            det = detections[det_idx]
            tid = self._next_track_id
            self._next_track_id += 1

            new_track = Track(
                track_id=tid,
                label=det.label,
                bbox=det.bbox,
                confidence=det.confidence,
                frame_id=det.frame_id,
                timestamp=utc_now(),
                age_frames=1,
                is_confirmed=True,
            )
            self._active_tracks[tid] = new_track
            self._lost_frame_counts[tid] = 0
            matched_tracks.append(new_track)

        return matched_tracks

    def reset(self) -> None:
        """Resets tracker state."""
        self._next_track_id = 1
        self._active_tracks.clear()
        self._lost_frame_counts.clear()
