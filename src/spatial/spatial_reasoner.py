# File: src/spatial/spatial_reasoner.py
import math
import logging
from typing import List, Dict, Optional, Tuple
from src.schemas.detection import BoundingBox, Landmark
from src.schemas.track import Track
from .scene import RackSceneLayout

logger = logging.getLogger(__name__)


def point_to_box_distance(point: Tuple[float, float], bbox: BoundingBox) -> float:
    """
    Computes minimum Euclidean distance from a 2D point (e.g. wrist/fingertip) to a bounding box.
    Returns 0.0 if the point is inside the box.
    """
    px, py = point
    dx = max(0.0, max(bbox.x1 - px, px - bbox.x2))
    dy = max(0.0, max(bbox.y1 - py, py - bbox.y2))
    return math.sqrt(dx * dx + dy * dy)


class SpatialReasoner:
    """
    Spatial reasoning engine for on-board BAS experiments.
    Manages rack coordinate zones and computes real-time hand-to-object spatial metrics.
    """

    def __init__(self, frame_width: int = 640, frame_height: int = 480):
        self.layout = RackSceneLayout(frame_width, frame_height)

    def update_object_zones(self, tracks: List[Track]) -> List[Track]:
        """
        Assigns spatial rack zones (e.g. 'A1', 'A2', 'TRAY') to all active tracks.

        Args:
            tracks: List of active Track objects.

        Returns:
            Updated list of Track objects with rack_zone populated.
        """
        for track in tracks:
            zone_name = self.layout.get_zone_for_box(track.bbox)
            track.rack_zone = zone_name
        return tracks

    def compute_hand_object_distances(
        self,
        tracks: List[Track],
        hand_landmarks: List[Landmark]
    ) -> Dict[int, float]:
        """
        Computes minimum Euclidean pixel distance from hand keypoints to each tracked object.

        Args:
            tracks: List of active Track objects.
            hand_landmarks: List of hand/wrist Landmark objects.

        Returns:
            Dictionary mapping track_id -> minimum distance to nearest hand keypoint.
        """
        distances: Dict[int, float] = {}

        if not hand_landmarks:
            for track in tracks:
                distances[track.track_id] = float("inf")
            return distances

        hand_points = [(lm.x, lm.y) for lm in hand_landmarks if lm.score >= 0.3]

        for track in tracks:
            if not hand_points:
                distances[track.track_id] = float("inf")
                continue

            min_dist = min(point_to_box_distance(pt, track.bbox) for pt in hand_points)
            distances[track.track_id] = round(min_dist, 1)

        return distances
