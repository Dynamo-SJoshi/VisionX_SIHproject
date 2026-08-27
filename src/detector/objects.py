# File: src/detector/objects.py
from typing import List, Dict, Any
import numpy as np


def detect_objects(frame: np.ndarray) -> List[Dict[str, Any]]:
    """
    Placeholder detector function simulating object detection results (e.g. sample container, tube, rack).

    Args:
        frame: OpenCV image frame array.

    Returns:
        List of object detection dicts containing label, confidence, and bounding box coordinates [x, y, w, h].
    """
    h, w, _ = frame.shape
    # Dummy mock detections for testing state pipeline
    return [
        {
            "label": "sample_container",
            "confidence": 0.94,
            "bbox": [int(w * 0.2), int(h * 0.3), 100, 120]
        },
        {
            "label": "sample_tube",
            "confidence": 0.89,
            "bbox": [int(w * 0.5), int(h * 0.4), 40, 90]
        },
        {
            "label": "rack",
            "confidence": 0.96,
            "bbox": [int(w * 0.7), int(h * 0.5), 120, 150]
        }
    ]
