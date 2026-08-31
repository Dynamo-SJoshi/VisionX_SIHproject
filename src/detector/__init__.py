# File: src/detector/__init__.py
"""
Detector module for object detection (YOLO) and pose estimation.
"""

from .inference import YOLOObjectDetector
from .objects import detect_objects, detect_objects_in_frame

__all__ = [
    "YOLOObjectDetector",
    "detect_objects",
    "detect_objects_in_frame"
]
