# File: src/tracker/identity.py
import math
from typing import Dict, List, Tuple, Optional
from collections import deque

from src.schemas.track import Track


class TrackHistoryManager:
    """
    Maintains spatial trajectories and displacement history for tracked entities.
    Enables detection of object movement, pickup, and placement.
    """

    def __init__(self, history_length: int = 30):
        self.history_length = history_length
        # Map track_id -> deque of (cx, cy) center points
        self.trajectories: Dict[int, deque] = {}

    def record_tracks(self, tracks: List[Track]) -> None:
        """Records current positions of active tracks into trajectory buffers."""
        for track in tracks:
            t_id = track.track_id
            if t_id not in self.trajectories:
                self.trajectories[t_id] = deque(maxlen=self.history_length)

            center = track.bbox.center
            self.trajectories[t_id].append(center)

    def get_displacement(self, track_id: int) -> float:
        """
        Calculates total Euclidean pixel displacement of track over its stored history.

        Args:
            track_id: Integer tracking ID.

        Returns:
            Displacement distance in pixels.
        """
        if track_id not in self.trajectories or len(self.trajectories[track_id]) < 2:
            return 0.0

        history = list(self.trajectories[track_id])
        start_pt = history[0]
        end_pt = history[-1]

        dx = end_pt[0] - start_pt[0]
        dy = end_pt[1] - start_pt[1]
        return math.sqrt(dx * dx + dy * dy)

    def is_moving(self, track_id: int, movement_threshold: float = 15.0) -> bool:
        """
        Determines if a tracked object has moved significantly.

        Args:
            track_id: Object tracking ID.
            movement_threshold: Minimum pixel displacement to consider moving.

        Returns:
            True if object is in motion, False if stationary.
        """
        return self.get_displacement(track_id) >= movement_threshold

    def get_trajectory(self, track_id: int) -> List[Tuple[float, float]]:
        """Returns trajectory point list for a track."""
        if track_id in self.trajectories:
            return list(self.trajectories[track_id])
        return []

    def reset(self) -> None:
        """Clears all stored trajectory histories."""
        self.trajectories.clear()
