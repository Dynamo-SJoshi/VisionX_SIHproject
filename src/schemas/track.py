"""
Tracking schemas.

A Track represents a persistent identity across frames.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import BBox, SchemaBase


class Track(SchemaBase):
    """
    Persistent object/person track.
    """

    track_id: int = Field(
        ge=0,
        description="Persistent tracker ID.",
    )

    label: str = Field(
        min_length=1,
        description="Tracked class label.",
    )

    bbox: BBox = Field(
        description="Current bounding box as (x1, y1, x2, y2).",
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Current tracking/detection confidence.",
    )

    frame_id: int = Field(
        ge=0,
        description="Current frame number.",
    )

    timestamp: datetime = Field(
        description="UTC timestamp of this track observation.",
    )

    age_frames: int = Field(
        default=1,
        ge=1,
        description="Number of frames this track has existed.",
    )

    is_confirmed: bool = Field(
        default=True,
        description="Whether the tracker considers the identity stable.",
    )
