"""
Spatial schemas for BAS-HAR.

The spatial module describes where entities are and how entities
relate to each other.

SpatialState:
    Describes the whole scene.

SpatialContext:
    Describes the spatial context attached to one action.

This separation keeps ActionEvent independent of the implementation
of the full spatial-reasoning subsystem.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import Field

from .common import SchemaBase


class ZoneType(str, Enum):
    """
    Semantic payload/rack zones.
    """

    SAMPLE_ZONE = "sample_zone"
    PROCESSING_ZONE = "processing_zone"
    TRANSFER_ZONE = "transfer_zone"
    STORAGE_ZONE = "storage_zone"
    TOOL_ZONE = "tool_zone"
    UNKNOWN = "unknown"


class Point3D(SchemaBase):
    """
    Position in a selected coordinate reference frame.
    """

    x: float
    y: float
    z: float


class SpatialRelation(SchemaBase):
    """
    Relationship between two entities.

    Example:
        astronaut_01 --holding--> pipette_01
    """

    subject_id: str = Field(
        min_length=1,
    )

    relation: str = Field(
        min_length=1,
    )

    object_id: str = Field(
        min_length=1,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )


class SpatialState(SchemaBase):
    """
    Scene-level spatial state.
    """

    timestamp: datetime

    rack_id: Optional[str] = None

    entity_positions: Dict[str, Point3D] = Field(
        default_factory=dict,
    )

    entity_zones: Dict[str, ZoneType] = Field(
        default_factory=dict,
    )

    relations: List[SpatialRelation] = Field(
        default_factory=list,
    )

    orientation_degrees: Optional[float] = Field(
        default=None,
        ge=-360.0,
        le=360.0,
    )