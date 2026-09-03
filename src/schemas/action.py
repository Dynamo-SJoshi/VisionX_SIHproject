# File: src/schemas/action.py
"""
Unified BAS-HAR Action Event Schemas.

Supports both M2 CV perception pipelines and M1/M3 Protocol/Decision engines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid

from pydantic import Field, model_validator

from .common import BBox, SchemaBase, utc_now


# ============================================================================
# ACTION TYPES & STATUSES
# ============================================================================

class ActionType(str, Enum):
    """Controlled vocabulary for BAS-HAR experiment actions."""
    IDENTIFY = "identify"
    APPROACH = "approach"
    PICK = "pick"
    HOLD = "hold"
    RELEASE = "release"
    OPEN = "open"
    CLOSE = "close"
    TRANSFER = "transfer"
    MIX = "mix"
    POUR = "pour"
    INSERT = "insert"
    REMOVE = "remove"
    SEAL = "seal"
    PLACE = "place"
    CONFIRM = "confirm"
    IDLE = "idle"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_lower = value.lower()
            for member in cls:
                if member.value == val_lower or member.name.lower() == val_lower:
                    return member
        return cls.UNKNOWN


class ActionStatus(str, Enum):
    """Uncertainty classification status for M2 pipeline."""
    CONFIRMED = "CONFIRMED"
    UNCERTAIN = "UNCERTAIN"


class EventStatus(str, Enum):
    """Lifecycle status of an action event for M1/M3 state machines."""
    CANDIDATE = "candidate"
    DETECTED = "detected"
    VALIDATED = "validated"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"


class HandType(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"
    UNKNOWN = "unknown"


class RecognitionSource(str, Enum):
    HEURISTIC = "heuristic"
    TEMPORAL_MODEL = "temporal_model"
    SPATIAL_RULES = "spatial_rules"
    HYBRID = "hybrid"
    MOCK = "mock"


# ============================================================================
# INTERACTION & CONTEXT SUB-SCHEMAS
# ============================================================================

class ObjectInteraction(SchemaBase):
    """Object participating in an action."""
    object_id: str = Field(min_length=1)
    object_label: Optional[str] = None
    role: str = Field(default="target")
    track_id: Optional[int] = None
    bbox: Optional[BBox] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class SpatialContext(SchemaBase):
    """Spatial context of an action event."""
    rack_zone: Optional[str] = None
    interaction_zone: Optional[str] = None
    rack_relative_position: Optional[List[float]] = None
    distance_to_target_cm: Optional[float] = None
    is_inside_rack: Optional[bool] = None


class ActionEvidence(SchemaBase):
    """Lightweight supporting evidence references."""
    start_frame_id: Optional[int] = None
    end_frame_id: Optional[int] = None
    snapshot_path: Optional[str] = None


# ============================================================================
# CANONICAL ACTION EVENT
# ============================================================================

class ActionEvent(SchemaBase):
    """
    Standardized M2/M3 Action Event representing an observed physical interaction.
    """
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    session_id: Optional[str] = Field(default="SESSION_01")
    sequence_number: Optional[int] = Field(default=1)
    timestamp: Union[datetime, float] = Field(default_factory=utc_now)

    action: ActionType = Field(..., description="Observed action type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Recognition confidence")

    # M2 perception fields
    object: Optional[str] = Field(default=None, description="Target object identifier")
    actor: Optional[str] = Field(default="astronaut_01", description="Actor performing action")
    rack_zone: Optional[str] = Field(default=None, description="Spatial rack zone")

    # M1/M3 structured fields
    actor_id: Optional[str] = Field(default=None)
    status: Union[EventStatus, ActionStatus, str] = Field(default=EventStatus.VALIDATED)
    target_object: Optional[ObjectInteraction] = Field(default=None)
    tool_object: Optional[ObjectInteraction] = Field(default=None)
    interaction_zone: Optional[str] = Field(default=None)
    spatial_context: Optional[SpatialContext] = Field(default=None)
    evidence: Optional[ActionEvidence] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if self.object and not self.target_object:
            self.target_object = ObjectInteraction(
                object_id=self.object,
                object_label=self.object,
                role="target",
                confidence=self.confidence,
            )
        elif self.target_object and not self.object:
            self.object = self.target_object.object_id

        if not self.actor_id and self.actor:
            self.actor_id = self.actor
        elif not self.actor and self.actor_id:
            self.actor = self.actor_id

        if self.rack_zone and not self.interaction_zone:
            self.interaction_zone = self.rack_zone
        elif self.interaction_zone and not self.rack_zone:
            self.rack_zone = self.interaction_zone

        if isinstance(self.timestamp, (int, float)):
            try:
                self.timestamp = datetime.fromtimestamp(self.timestamp, tz=timezone.utc)
            except Exception:
                self.timestamp = datetime.now(timezone.utc)
