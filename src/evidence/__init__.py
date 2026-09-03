# File: src/evidence/__init__.py
"""
Evidence capture, snapshot, and management modules for BAS HAR Assistant.
"""

from .evidence_manager import EvidenceManager
from .snapshot import save_image_frame

__all__ = ["EvidenceManager", "save_image_frame"]
