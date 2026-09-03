"""
Common schema utilities for BAS-HAR.

All project schemas inherit from SchemaBase so that:
- unexpected fields are rejected
- assignment validation is enabled
- enums are serialized as their values
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple

from pydantic import BaseModel, ConfigDict


# Bounding box convention:
# (x1, y1, x2, y2)
BBox = Tuple[int, int, int, int]


def utc_now() -> datetime:
    """
    Return the current time as a timezone-aware UTC datetime.
    """
    return datetime.now(timezone.utc)


class SchemaBase(BaseModel):
    """
    Base class used by all BAS-HAR Pydantic models.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True,
    )