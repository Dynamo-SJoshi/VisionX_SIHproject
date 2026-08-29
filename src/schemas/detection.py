from __future__ import annotations
from typing import Optional
from pydantic import Field
from .common import BBox, ConfidenceMixin, TimestampMixin

class Detection(ConfidenceMixin, TimestampMixin):
    """Represents a single object/person detection produced by the perception layer."""
    detection_id: str = Field(
        min_length=1,
        description="Unique ID for this detection instance.",
    )
    label: str = Field(
        min_length=1,
        description="Detected class label, e.g. tube, pipette, worker.",
    )
    bbox: BBox = Field(
        description="Bounding box as (x1, y1, x2, y2) in pixel coordinates.",
    )
    frame_id: int = Field(
        ge=0,
        description="Frame number from the input video stream.",
    )
    source_camera: Optional[str] = Field(
        default=None,
        description="Camera identifier, e.g. CAM-01.",
    )