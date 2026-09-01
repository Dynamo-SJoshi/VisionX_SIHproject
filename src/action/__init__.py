# File: src/action/__init__.py
"""
Action recognition and hand-object interaction detection module for M2 pipeline.
"""

from .action_rules import InteractionType, HandObjectInteraction, HandObjectInteractionDetector

__all__ = [
    "InteractionType",
    "HandObjectInteraction",
    "HandObjectInteractionDetector"
]
