# File: src/detector/__init__.py
"""
Detector stubs module for object detection and pose estimation.
"""

from .objects import detect_objects
from .pose import estimate_pose

__all__ = ["detect_objects", "estimate_pose"]
