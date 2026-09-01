# File: src/schemas/__init__.py
"""
Unified Pydantic Data Schemas for M2 AI Perception & Protocol Engine.
"""

from .detection import BoundingBox, Landmark, Detection, DetectionFrame
from .track import Track
from .action import ActionType, ActionStatus, ActionEvent

__all__ = [
    "BoundingBox",
    "Landmark",
    "Detection",
    "DetectionFrame",
    "Track",
    "ActionType",
    "ActionStatus",
    "ActionEvent"
]
