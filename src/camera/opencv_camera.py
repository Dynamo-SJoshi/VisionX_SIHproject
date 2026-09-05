# File: src/camera/opencv_camera.py
import time
import logging
from typing import Union, Optional, Tuple, Any
import numpy as np

from src.interfaces.camera import CameraInterface
from src.camera.capture import CameraCapture

logger = logging.getLogger(__name__)


class OpenCVCamera(CameraInterface):
    """
    OpenCV live webcam and video file camera conforming to CameraInterface.
    Wraps CameraCapture for USB webcam, RTSP, and local video file inputs.
    """

    def __init__(self, source: Union[int, str] = 0, width: int = 640, height: int = 480):
        self.source = source
        self.width = width
        self.height = height
        self._cam: Optional[CameraCapture] = None
        self._running = False

    def start(self) -> None:
        """Initializes and opens the camera capture device."""
        if self._cam is None:
            self._cam = CameraCapture(source=self.source, width=self.width, height=self.height)
        self._running = True
        logger.info(f"OpenCVCamera started on source: {self.source}")

    def read(self) -> Tuple[np.ndarray, float]:
        """
        Reads next frame from the camera.

        Returns:
            Tuple of (OpenCV BGR ndarray, float timestamp).
        """
        if not self._running or self._cam is None:
            self.start()

        frame, ts_str = self._cam.read_frame()
        return frame, time.time()

    def stop(self) -> None:
        """Releases the camera device."""
        if self._cam is not None:
            self._cam.release()
            self._cam = None
        self._running = False
        logger.info("OpenCVCamera stopped.")

    def is_running(self) -> bool:
        """Returns True if camera is actively running."""
        return self._running and (self._cam is not None)
