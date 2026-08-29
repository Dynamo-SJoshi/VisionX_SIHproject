"""
Object detection interface for BAS-HAR.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Any

from src.schemas.detection import Detection


class DetectorInterface(ABC):
    """
    Contract for object/person detection implementations.

    Example implementation:
        YOLODetector

    Example test implementation:
        MockDetector
    """

    @abstractmethod
    def detect(self, frame: Any) -> List[Detection]:
        """
        Detect objects/persons in a single frame.

        Args:
            frame:
                Input image/frame.

        Returns:
            List[Detection]:
                All valid detections from the frame.
        """
        raise NotImplementedError

    def name(self) -> str:
        """
        Human-readable detector name.
        """
        return self.__class__.__name__

    def is_ready(self) -> bool:
        """
        Optional readiness check.

        Concrete detectors can override this.
        """
        return True