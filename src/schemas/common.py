from __future__ import annotations
from datetime import datetime, timezone
from typing import Tuple
from pydantic import BaseModel, ConfigDict, Field

# Common reusable types
BBox = Tuple[int, int, int, int]

def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)

class SchemaBase(BaseModel):
    """
    Base class for all project schemas.
    extra='forbid' means if a module sends unexpected fields, it crashes immediately
    instead of silently accepting malformed data.
    """
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True,
    )

class ConfidenceMixin(SchemaBase):
    """Shared confidence field. Must always be between 0 and 1."""
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model confidence in the prediction, in the range [0, 1].",
    )

class TimestampMixin(SchemaBase):
    """Shared timestamp. Store timestamps as UTC-aware datetimes."""
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp associated with the event.",
    )