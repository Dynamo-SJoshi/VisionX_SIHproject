"""
Action recognition interface for BAS-HAR.

The action-recognition layer converts lower-level perception/tracking
information into semantic ActionEvent objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.schemas.action import ActionEvent
from src.schemas.track import Track
from src.schemas.spatial import SpatialState


class ActionRecognizerInterface(ABC):
    """
    Contract for action-recognition implementations.

    Example:
        YOLO + MediaPipe + temporal rules
        Temporal neural network
        Hybrid model/rule engine
        Mock recognizer
    """

    @abstractmethod
    def recognize(
        self,
        tracks: List[Track],
        spatial_state: Optional[SpatialState] = None,
    ) -> Optional[ActionEvent]:
        """
        Recognize a semantic action from tracked entities.

        Args:
            tracks:
                Current tracked objects/persons.

            spatial_state:
                Optional spatial understanding of the scene.

        Returns:
            ActionEvent | None:
                A recognized action event when sufficient evidence
                exists. None when there is no action event to emit.
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """
        Clear temporal/action-recognition state.
        """
        raise NotImplementedError

    def name(self) -> str:
        """
        Human-readable recognizer name.
        """
        return self.__class__.__name__