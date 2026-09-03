# File: src/tracker/__init__.py
"""
Persistent multi-object tracking and trajectory identity management module.
"""

from .track import ObjectTracker
from .identity import TrackHistoryManager

__all__ = [
    "ObjectTracker",
    "TrackHistoryManager"
]
