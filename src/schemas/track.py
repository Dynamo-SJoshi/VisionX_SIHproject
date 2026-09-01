# File: src/schemas/track.py
from typing import Optional, Tuple
from pydantic import BaseModel, Field
from .detection import BoundingBox


class Track(BaseModel):
    """Persistent object or entity track maintained across frames by ByteTrack/BoT-SORT."""
    track_id: int = Field(..., description="Unique persistent integer tracking ID")
    class_name: str = Field(..., description="Object class label")
    bbox: BoundingBox = Field(..., description="Current frame bounding box")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    velocity: Tuple[float, float] = Field(default=(0.0, 0.0), description="Velocity vector (dx, dy)")
    rack_zone: Optional[str] = Field(default=None, description="Current rack spatial zone (e.g. A1, A2)")
    age: int = Field(default=1, description="Total number of frames tracked")
    hits: int = Field(default=1, description="Total number of detection matches")
