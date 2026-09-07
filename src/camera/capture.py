# File: src/camera/capture.py
import datetime
import logging
import sys
from typing import Tuple, Union, Optional, Any
import numpy as np
import cv2

from src.interfaces.camera import CameraInterface

logger = logging.getLogger(__name__)


class CameraCapture(CameraInterface):
    """Handles camera capture from USB devices, RTSP streams, or synthetic fallback frames."""

    def __init__(self, source: Union[int, str] = 0, width: int = 640, height: int = 480):
        self.source = source
        self.width = width
        self.height = height
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_synthetic: bool = False
        self._running: bool = False
        self._init_camera()

    def _init_camera(self) -> None:
        """Attempts to initialize OpenCV VideoCapture object."""
        # Pick the right backend per OS:
        # - Linux: V4L2 (Video4Linux2)
        # - Windows: DSHOW (DirectShow)
        # - Others: let OpenCV auto-select
        if sys.platform.startswith("linux"):
            backends = [cv2.CAP_V4L2, 0]  # 0 = auto-fallback
        elif sys.platform == "win32":
            backends = [cv2.CAP_DSHOW, 0]
        else:
            backends = [0]

        for backend in backends:
            try:
                self.cap = cv2.VideoCapture(self.source, backend) if backend != 0 else cv2.VideoCapture(self.source)
                if self.cap.isOpened():
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    backend_name = {cv2.CAP_V4L2: "V4L2", cv2.CAP_DSHOW: "DSHOW"}.get(backend, "AUTO")
                    logger.info(f"Successfully opened camera source {self.source} via {backend_name}.")
                    self._running = True
                    return
                else:
                    logger.debug(f"Backend {backend} failed for source {self.source}, trying next.")
            except Exception as e:
                logger.debug(f"Backend {backend} raised exception: {e}")

        logger.warning(f"Could not open camera source {self.source} with any backend. Falling back to synthetic feed.")
        self.is_synthetic = True
        self._running = True

    def _generate_synthetic_frame(self) -> np.ndarray:
        """Generates a dummy test video frame when no live camera hardware is available."""
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Gradient background
        for y in range(self.height):
            frame[y, :, 0] = int(y / self.height * 100)
            frame[y, :, 1] = int(y / self.height * 150)
            frame[y, :, 2] = 120

        # Draw overlay text
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        cv2.putText(frame, "BAS HAR Assistant - Offline Synthetic Feed", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Timestamp: {timestamp_str}", (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(frame, "Simulating On-board Video Feed...", (20, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        return frame

    def start(self) -> None:
        """Starts camera stream."""
        if not self._running:
            self._init_camera()

    def read(self) -> np.ndarray:
        """Implements CameraInterface.read returning ndarray."""
        frame, _ = self.read_frame()
        return frame

    def read_frame(self) -> Tuple[np.ndarray, str]:
        """
        Reads next video frame.

        Returns:
            Tuple of (frame numpy array, ISO 8601 timestamp string).
        """
        timestamp = datetime.datetime.now().isoformat()

        if self.is_synthetic or self.cap is None or not self.cap.isOpened():
            frame = self._generate_synthetic_frame()
            return frame, timestamp

        ret, frame = self.cap.read()
        if not ret or frame is None:
            logger.warning("Failed to read frame from live camera. Generating synthetic frame.")
            frame = self._generate_synthetic_frame()
        else:
            # Mirror the frame across the Y-axis
            frame = cv2.flip(frame, 1)

        return frame, timestamp

    def stop(self) -> None:
        """Stops camera stream."""
        self.release()

    def is_running(self) -> bool:
        """Returns whether the camera is actively capturing."""
        return self._running

    def release(self) -> None:
        """Releases camera resources."""
        self._running = False
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
            logger.info("Camera capture hardware released.")

