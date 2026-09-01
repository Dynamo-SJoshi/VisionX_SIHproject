# File: src/detector/__init__.py
"""
Detector module for object detection (YOLO), pose estimation, and hand landmark tracking.
"""

from .inference import YOLOObjectDetector
from .objects import detect_objects, detect_objects_in_frame
from .pose import MediaPipePoseEstimator
from .hands import MediaPipeHandEstimator

__all__ = [
    "YOLOObjectDetector",
    "detect_objects",
    "detect_objects_in_frame",
    "MediaPipePoseEstimator",
    "MediaPipeHandEstimator"
]
