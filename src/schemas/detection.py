"""
Detection schemas.

A Detection represents an object/person detected in a single frame.
It is NOT a persistent identity. Persistence is handled by Track.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from .common import BBox, SchemaBase, utc_now
from datetime import datetime


class Detection(SchemaBase):
    """
    Single-frame perception result.
    """

    detection_id: str = Field(
        min_length=1,
        description="Unique identifier for this detection instance.",
    )

    label: str = Field(
        min_length=1,
        description="Detected class label.",
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Detection confidence in the range [0, 1].",
    )

    bbox: BBox = Field(
        description="Bounding box as (x1, y1, x2, y2).",
    )

    frame_id: int = Field(
        ge=0,
        description="Frame number in the input stream.",
    )

    timestamp: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp associated with this detection.",
    )

    source_camera: Optional[str] = Field(
        default=None,
        description="Camera identifier such as CAM-01.",
    )
