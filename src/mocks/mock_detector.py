"""
Mock detector for BAS-HAR integration testing.
"""

from __future__ import annotations

from typing import Any, List

from src.interfaces.detector import DetectorInterface
from src.schemas.detection import Detection
from src.schemas.common import utc_now


class MockDetector(DetectorInterface):
    """
    Synthetic detector producing deterministic detections.
    """

    def detect(self, frame: Any) -> List[Detection]:
        """
        Generate a synthetic tube detection for the current frame.
        """

        print("[DETECTOR] Processing frame")

        frame_id = 0

        if isinstance(frame, dict):
            frame_id = frame.get("frame_id", 0)

        detection = Detection(
            detection_id=f"det_mock_{frame_id:04d}",
            label="tube",
            confidence=0.95,
            bbox=(100, 120, 200, 250),
            frame_id=frame_id,
            source_camera="CAM-MOCK",
            timestamp=utc_now(),
        )

        return [detection]

    def is_ready(self) -> bool:
        """Mock detector is always ready."""
        return True