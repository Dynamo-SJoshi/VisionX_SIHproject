"""
Mock tracker for BAS-HAR integration testing.
"""

from __future__ import annotations

from typing import List

from src.interfaces.tracker import TrackerInterface
from src.schemas.detection import Detection
from src.schemas.track import Track
from src.schemas.common import utc_now


class MockTracker(TrackerInterface):
    """
    Deterministic tracker.

    Each detected object is assigned a stable track ID based on its
    position in the detection list.
    """

    def __init__(self) -> None:
        self._next_track_id = 1

    def update(
        self,
        detections: List[Detection],
    ) -> List[Track]:

        print("[TRACKER] Updating tracks")

        tracks: List[Track] = []

        for index, detection in enumerate(detections):

            track = Track(
                track_id=index + 1,
                label=detection.label,
                bbox=detection.bbox,
                confidence=detection.confidence,
                frame_id=detection.frame_id,
                timestamp=utc_now(),
                age_frames=5,
                is_confirmed=True,
            )

            tracks.append(track)

        return tracks

    def reset(self) -> None:
        """Reset tracker state."""
        self._next_track_id = 1