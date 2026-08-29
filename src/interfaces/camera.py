from abc import ABC, abstractmethod
from typing import Any


class CameraInterface(ABC):
    """
    Abstract base class for all camera or video stream input sources.
    """

    @abstractmethod
    def start(self) -> None:
        """Initialize and start the camera stream."""
        pass

    @abstractmethod
    def read(self) -> Any:
        """
        Read the next frame from the stream.
        
        Returns:
            Frame data (e.g., numpy array or structured frame dictionary).
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Release camera resources and terminate stream."""
        pass