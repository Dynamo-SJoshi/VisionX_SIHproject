"""
Camera interface for BAS-HAR.

The camera implementation may use:
    - USB webcam
    - OpenCV VideoCapture
    - RTSP stream
    - recorded video
    - synthetic/mock source

The rest of the system must not depend on the concrete implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CameraInterface(ABC):
    """
    Contract that every BAS-HAR camera implementation must follow.
    """

    @abstractmethod
    def start(self) -> None:
        """
        Start the camera/video source.

        Raises:
            RuntimeError:
                If the camera cannot be initialized.
        """
        raise NotImplementedError

    @abstractmethod
    def read(self) -> Any:
        """
        Read the next frame.

        Returns:
            Any:
                The concrete frame representation.

                For OpenCV this will normally be a numpy.ndarray.

        Raises:
            RuntimeError:
                If the camera is not running or frame acquisition fails.
        """
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """
        Stop and release the camera/video source.
        """
        raise NotImplementedError

    def is_running(self) -> bool:
        """
        Optional health check.

        Concrete implementations can override this method.
        """
        return False