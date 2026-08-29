"""
Object/person tracking interface for BAS-HAR.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.schemas.detection import Detection
from src.schemas.track import Track


class TrackerInterface(ABC):
    """
    Contract for all object/person tracking implementations.
    """

    @abstractmethod
    def update(
        self,
        detections: List[Detection],
    ) -> List[Track]:
        """
        Update tracker state using detections from the current frame.

        Args:
            detections:
                Detections belonging to the current frame.

        Returns:
            List[Track]:
                Current active tracks.
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """
        Clear all tracker state.

        This should normally be called when:
            - a new experiment starts
            - a video restarts
            - the camera source changes
        """
        raise NotImplementedError

    def name(self) -> str:
        """
        Human-readable tracker name.
        """
        return self.__class__.__name__