from abc import ABC, abstractmethod
from typing import Any, List
from src.schemas.detection import Detection


class DetectorInterface(ABC):
    """
    Abstract base class for object and keypoint detectors.
    """

    @abstractmethod
    def detect(self, frame: Any) -> List[Detection]:
        """
        Process a single image frame and return detected objects.
        
        Args:
            frame: Raw image frame.
            
        Returns:
            List of standardized Detection schema instances.
        """
        pass