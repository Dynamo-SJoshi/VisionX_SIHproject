from abc import ABC, abstractmethod
from typing import List
from src.schemas.detection import Detection
from src.schemas.track import Track


class TrackerInterface(ABC):
    """
    Abstract base class for spatial/temporal object tracking algorithms.
    """

    @abstractmethod
    def update(self, detections: List[Detection]) -> List[Track]:
        """
        Update the tracker state with new detections from the current frame.
        
        Args:
            detections: List of Detection instances from the detector.
            
        Returns:
            List of active Track schema instances with persistent IDs.
        """
        pass