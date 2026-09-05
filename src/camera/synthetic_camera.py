# File: src/camera/synthetic_camera.py
import time
import numpy as np
from typing import Tuple, Optional
from src.interfaces.camera import CameraInterface


class SyntheticCamera(CameraInterface):
    """
    Synthetic mock camera implementation for headless tests, CI/CD, and offline simulations.
    Generates synthetic BGR frames with simulated experiment timestamp.
    """

    def __init__(self, width: int = 640, height: int = 480, fps: float = 30.0):
        self.width = width
        self.height = height
        self.fps = fps
        self._running = False
        self._frame_count = 0

    def start(self) -> None:
        """Starts synthetic frame generation."""
        self._running = True
        self._frame_count = 0

    def read(self) -> Tuple[np.ndarray, float]:
        """
        Generates and returns synthetic BGR frame.

        Returns:
            Tuple of (numpy ndarray frame, float timestamp).
        """
        if not self._running:
            self.start()

        self._frame_count += 1
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Add light gray background
        frame[:] = (40, 40, 40)
        timestamp = time.time()
        return frame, timestamp

    def stop(self) -> None:
        """Stops synthetic camera."""
        self._running = False

    def is_running(self) -> bool:
        """Returns True if synthetic camera is active."""
        return self._running
