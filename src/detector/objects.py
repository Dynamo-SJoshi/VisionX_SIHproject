# File: src/detector/objects.py
from typing import List, Optional
import numpy as np

from src.schemas.detection import Detection, DetectionFrame
from .inference import YOLOObjectDetector

_default_detector: Optional[YOLOObjectDetector] = None


def get_default_detector() -> YOLOObjectDetector:
    """Returns or creates singleton default detector instance."""
    global _default_detector
    if _default_detector is None:
        _default_detector = YOLOObjectDetector()
    return _default_detector


def detect_objects(frame: np.ndarray, detector: Optional[YOLOObjectDetector] = None) -> List[Detection]:
    """
    Detects experiment objects in a frame.

    Args:
        frame: OpenCV image array (H, W, 3).
        detector: Optional custom YOLOObjectDetector instance.

    Returns:
        List of typed Detection objects.
    """
    if detector is None:
        detector = get_default_detector()
    return detector.detect(frame)


def detect_objects_in_frame(
    frame: np.ndarray,
    timestamp: float = 0.0,
    frame_index: int = 0,
    detector: Optional[YOLOObjectDetector] = None
) -> DetectionFrame:
    """
    Runs detection on frame and wraps output into a DetectionFrame container.

    Args:
        frame: OpenCV image array.
        timestamp: Frame capture timestamp in seconds.
        frame_index: Sequential frame number.
        detector: Optional custom detector instance.

    Returns:
        DetectionFrame containing object detections.
    """
    detections = detect_objects(frame, detector=detector)
    return DetectionFrame(
        frame_index=frame_index,
        timestamp=timestamp,
        detections=detections
    )
