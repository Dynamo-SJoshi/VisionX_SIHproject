"""
Mock camera implementation for BAS-HAR integration testing.

This produces synthetic frames so the complete pipeline can be tested
without requiring a physical camera.
"""

from __future__ import annotations

import time
from typing import Any, Dict

from src.interfaces.camera import CameraInterface


class MockCamera(CameraInterface):
    """
    Synthetic camera source.

    The returned object intentionally behaves like a lightweight frame
    container rather than a numpy image. This keeps Day-2 integration tests
    independent from OpenCV.
    """

    def __init__(self) -> None:
        self._running = False
        self._frame_id = 0

    def start(self) -> None:
        """Start the mock camera."""
        self._running = True
        self._frame_id = 0

        print("[CAMERA] Mock camera started")

    def read(self) -> Dict[str, Any]:
        """
        Return the next synthetic frame.

        Raises:
            RuntimeError:
                If read() is called before start().
        """

        if not self._running:
            raise RuntimeError(
                "Mock camera is not running. Call start() first."
            )

        self._frame_id += 1

        return {
            "frame_id": self._frame_id,
            "timestamp": time.time(),
            "data": "fake_image_data",
            "source": "MOCK",
        }

    def stop(self) -> None:
        """Stop the mock camera."""
        self._running = False

        print("[CAMERA] Mock camera stopped")

    def is_running(self) -> bool:
        """Return whether the camera is active."""
        return self._running