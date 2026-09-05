# File: src/detector/__init__.py
"""
Detector module for object detection and pose estimation.
"""

from .inference import YOLODetector
from .objects import detect_objects
from .pose import estimate_pose

__all__ = ["YOLODetector", "detect_objects", "estimate_pose"]

