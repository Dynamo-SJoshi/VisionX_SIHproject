# File: src/schemas/track.py
"""
Unified Tracking schemas for BAS-HAR.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple, Union
from pydantic import Field

from .common import BBox, SchemaBase, utc_now
from .detection import BoundingBox


class Track(SchemaBase):
    """
    Persistent object/person track across frames.
    Supports both M2 pipeline attributes and M1/M3 audit contracts.
    """

    track_id: int = Field(..., description="Unique persistent integer tracking ID")
    class_name: Optional[str] = Field(default=None, description="Object class label")
    label: Optional[str] = Field(default=None, description="Tracked class label alias")
    bbox: Union[BoundingBox, BBox] = Field(..., description="Current frame bounding box")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection / tracking confidence score")
    velocity: Tuple[float, float] = Field(default=(0.0, 0.0), description="Velocity vector (dx, dy)")
    rack_zone: Optional[str] = Field(default=None, description="Current rack spatial zone (e.g. A1, A2)")
    age: int = Field(default=1, description="Total number of frames tracked")
    hits: int = Field(default=1, description="Total number of detection matches")
    frame_id: Optional[int] = Field(default=0, ge=0, description="Current frame number")
    timestamp: Optional[datetime] = Field(default_factory=utc_now, description="UTC timestamp of observation")
    is_confirmed: bool = Field(default=True, description="Whether tracker considers identity stable")

    def model_post_init(self, __context: any) -> None:
        if self.class_name and not self.label:
            self.label = self.class_name
        elif self.label and not self.class_name:
            self.class_name = self.label
