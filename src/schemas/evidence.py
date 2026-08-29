from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import Field
from .common import SchemaBase

class EvidenceType(str, Enum):
    VISUAL = "visual"
    SENSOR = "sensor"
    OPERATOR = "operator"

class EvidenceItem(SchemaBase):
    """A single piece of evidence supporting an action/decision."""
    evidence_id: str = Field(min_length=1)
    evidence_type: EvidenceType
    timestamp: datetime
    camera_id: Optional[str] = None
    frame_id: Optional[int] = Field(default=None, ge=0)
    video_timestamp_seconds: Optional[float] = Field(default=None, ge=0.0)
    snapshot_path: Optional[str] = None
    video_path: Optional[str] = None
    description: str = Field(min_length=1)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

class EvidenceBundle(SchemaBase):
    """Collection of evidence associated with one decision/event."""
    evidence_id: str = Field(min_length=1)
    action_event_id: Optional[str] = None
    decision_id: Optional[str] = None
    items: List[EvidenceItem] = Field(default_factory=list)