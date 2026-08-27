# File: src/tracker/track.py
from typing import List, Dict, Any


class ObjectTracker:
    """Simple object/person tracking stub maintaining entity track IDs across frames."""

    def __init__(self):
        self.next_track_id = 1
        self.tracks: Dict[int, Dict[str, Any]] = {}

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Updates tracked objects with new frame detections.

        Args:
            detections: List of detection dictionaries.

        Returns:
            List of tracked objects updated with persistent `track_id`.
        """
        tracked_results = []
        for i, det in enumerate(detections):
            track_id = i + 1  # Simple mock tracking ID assignment
            tracked_obj = dict(det)
            tracked_obj["track_id"] = track_id
            tracked_results.append(tracked_obj)

        return tracked_results
