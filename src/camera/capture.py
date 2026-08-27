# File: src/camera/capture.py
import datetime
import logging
from typing import Tuple, Union, Optional
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class CameraCapture:
    """Handles camera capture from USB devices, RTSP streams, or synthetic fallback frames."""

    def __init__(self, source: Union[int, str] = 0, width: int = 640, height: int = 480):
        self.source = source
        self.width = width
        self.height = height
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_synthetic: bool = False
        self._init_camera()

    def _init_camera(self) -> None:
        """Attempts to initialize OpenCV VideoCapture object."""
        try:
            self.cap = cv2.VideoCapture(self.source)
            if not self.cap.isOpened():
                logger.warning(f"Could not open camera source {self.source}. Falling back to synthetic feed.")
                self.is_synthetic = True
            else:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                logger.info(f"Successfully opened camera source {self.source}.")
        except Exception as e:
            logger.error(f"Error initializing camera source {self.source}: {e}. Enabling synthetic feed.")
            self.is_synthetic = True

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

        return frame, timestamp

    def release(self) -> None:
        """Releases camera resources."""
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
            logger.info("Camera capture hardware released.")
