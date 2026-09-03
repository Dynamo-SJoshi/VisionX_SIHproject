"""
BAS-HAR Action Event Schema.

ActionEvent is the canonical output of the action-recognition layer.

It answers:

    "What does the perception/action layer believe happened?"

It does NOT answer:

    "Was that action valid according to the experiment?"

Protocol validation is performed by protocol.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import Field, model_validator

from .common import BBox, SchemaBase


# ============================================================================
# ACTION TYPES
# ============================================================================

class ActionType(str, Enum):
    """
    Controlled vocabulary for BAS-HAR experiment actions.
    """

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
    UNSEAL = "unseal"

    PLACE = "place"
    MOVE = "move"

    PRESS = "press"
    TURN = "turn"
    ROTATE = "rotate"

    CONFIRM = "confirm"

    UNKNOWN = "unknown"


# ============================================================================
# HAND
# ============================================================================

class HandType(str, Enum):
    """
    Hand involved in the interaction.
    """

    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"
    UNKNOWN = "unknown"


# ============================================================================
# RECOGNITION SOURCE
# ============================================================================

class RecognitionSource(str, Enum):
    """
    How the ActionEvent was generated.
    """

    MODEL = "model"
    RULE = "rule"
    HYBRID = "hybrid"
    MOCK = "mock"


# ============================================================================
# EVENT STATUS
# ============================================================================

class EventStatus(str, Enum):
    """
    Confidence state of the action-recognition result.

    This is NOT protocol validity.

    VALIDATED:
        Enough evidence exists to emit the event.

    UNCERTAIN:
        Evidence is insufficient.

    REJECTED:
        Candidate action was not trusted.
    """

    VALIDATED = "validated"
    UNCERTAIN = "uncertain"
    REJECTED = "rejected"


# ============================================================================
# OBJECT PARTICIPANT
# ============================================================================

class ObjectInteraction(SchemaBase):
    """
    An object participating in an action.
    """

    object_id: str = Field(
        min_length=1,
    )

    object_label: Optional[str] = Field(
        default=None,
    )

    role: str = Field(
        default="target",
        min_length=1,
        description=(
            "Role such as target, tool, source, destination."
        ),
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in object identity.",
    )

    bbox: Optional[BBox] = Field(
        default=None,
        description="Object bounding box as (x1, y1, x2, y2).",
    )


# ============================================================================
# SPATIAL CONTEXT
# ============================================================================

class SpatialContext(SchemaBase):
    """
    Spatial context associated with one ActionEvent.
    """

    rack_id: Optional[str] = Field(
        default=None,
    )

    zone: Optional[str] = Field(
        default=None,
    )

    x: Optional[float] = Field(
        default=None,
    )

    y: Optional[float] = Field(
        default=None,
    )

    z: Optional[float] = Field(
        default=None,
    )

    reference_frame: Optional[str] = Field(
        default=None,
        description=(
            "Coordinate reference frame, e.g. rack or camera."
        ),
    )

    source_camera: Optional[str] = Field(
        default=None,
    )

    orientation_degrees: Optional[float] = Field(
        default=None,
        ge=-360.0,
        le=360.0,
    )


# ============================================================================
# ACTION EVIDENCE
# ============================================================================

class ActionEvidence(SchemaBase):
    """
    Lightweight references to the evidence supporting an action.

    Actual files remain in the evidence subsystem.
    """

    frame_ids: List[int] = Field(
        default_factory=list,
    )

    video_timestamp_start: Optional[float] = Field(
        default=None,
        ge=0.0,
    )

    video_timestamp_end: Optional[float] = Field(
        default=None,
        ge=0.0,
    )

    snapshot_paths: List[str] = Field(
        default_factory=list,
    )

    video_path: Optional[str] = Field(
        default=None,
    )

    camera_ids: List[str] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_video_window(self) -> "ActionEvidence":

        if (
            self.video_timestamp_start is not None
            and self.video_timestamp_end is not None
            and self.video_timestamp_end
            < self.video_timestamp_start
        ):
            raise ValueError(
                "video_timestamp_end must be greater than or equal "
                "to video_timestamp_start."
            )

        return self


# ============================================================================
# MAIN ACTION EVENT
# ============================================================================

class ActionEvent(SchemaBase):
    """
    Canonical event produced by the action-recognition layer.
    """

    # ------------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------------

    event_id: str = Field(
        min_length=1,
    )

    session_id: str = Field(
        min_length=1,
    )

    sequence_number: int = Field(
        ge=0,
    )

    # ------------------------------------------------------------------------
    # Time
    # ------------------------------------------------------------------------

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    start_timestamp: Optional[datetime] = Field(
        default=None,
    )

    end_timestamp: Optional[datetime] = Field(
        default=None,
    )

    frame_start: Optional[int] = Field(
        default=None,
        ge=0,
    )

    frame_end: Optional[int] = Field(
        default=None,
        ge=0,
    )

    # ------------------------------------------------------------------------
    # Actor
    # ------------------------------------------------------------------------

    actor_id: str = Field(
        min_length=1,
    )

    hand: HandType = Field(
        default=HandType.UNKNOWN,
    )

    # ------------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------------

    action: ActionType

    action_label: Optional[str] = Field(
        default=None,
    )

    # ------------------------------------------------------------------------
    # Objects
    # ------------------------------------------------------------------------

    target_object: Optional[ObjectInteraction] = None

    tool_object: Optional[ObjectInteraction] = None

    source_object: Optional[ObjectInteraction] = None

    destination_object: Optional[ObjectInteraction] = None

    related_objects: List[ObjectInteraction] = Field(
        default_factory=list,
    )

    # ------------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------------

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    status: EventStatus = Field(
        default=EventStatus.VALIDATED,
    )

    recognition_source: RecognitionSource = Field(
        default=RecognitionSource.HYBRID,
    )

    actor_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    object_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    interaction_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    temporal_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    spatial_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    # ------------------------------------------------------------------------
    # Spatial
    # ------------------------------------------------------------------------

    spatial_context: Optional[SpatialContext] = None

    interaction_zone: Optional[str] = Field(
        default=None,
    )

    # ------------------------------------------------------------------------
    # Tracking references
    # ------------------------------------------------------------------------

    supporting_track_ids: List[int] = Field(
        default_factory=list,
    )

    supporting_detection_ids: List[str] = Field(
        default_factory=list,
    )

    # ------------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------------

    evidence: Optional[ActionEvidence] = None

    # ------------------------------------------------------------------------
    # Duration
    # ------------------------------------------------------------------------

    duration_seconds: Optional[float] = Field(
        default=None,
        ge=0.0,
    )

    # ------------------------------------------------------------------------
    # Explanation
    # ------------------------------------------------------------------------

    reasoning_summary: Optional[str] = None

    # ------------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------------

    metadata: Dict[str, str] = Field(
        default_factory=dict,
    )

    # ========================================================================
    # VALIDATORS
    # ========================================================================

    @model_validator(mode="after")
    def validate_temporal_information(
        self,
    ) -> "ActionEvent":

        if self.timestamp.tzinfo is None:
            raise ValueError(
                "timestamp must be timezone-aware."
            )

        if (
            self.start_timestamp is not None
            and self.start_timestamp.tzinfo is None
        ):
            raise ValueError(
                "start_timestamp must be timezone-aware."
            )

        if (
            self.end_timestamp is not None
            and self.end_timestamp.tzinfo is None
        ):
            raise ValueError(
                "end_timestamp must be timezone-aware."
            )

        if (
            self.start_timestamp is not None
            and self.end_timestamp is not None
            and self.end_timestamp < self.start_timestamp
        ):
            raise ValueError(
                "end_timestamp cannot be earlier than "
                "start_timestamp."
            )

        if (
            self.frame_start is not None
            and self.frame_end is not None
            and self.frame_end < self.frame_start
        ):
            raise ValueError(
                "frame_end cannot be earlier than frame_start."
            )

        return self

    @model_validator(mode="after")
    def validate_uncertainty(
        self,
    ) -> "ActionEvent":

        if (
            self.status == EventStatus.UNCERTAIN
            and self.confidence >= 0.95
        ):
            raise ValueError(
                "An UNCERTAIN event should not have confidence "
                ">= 0.95."
            )

        return self

    # ========================================================================
    # HELPERS
    # ========================================================================

    def involves_object(
        self,
        object_id: str,
    ) -> bool:
        """
        Return True if object_id participates in the action.
        """

        if not object_id:
            return False

        objects = [
            self.target_object,
            self.tool_object,
            self.source_object,
            self.destination_object,
            *self.related_objects,
        ]

        return any(
            obj is not None
            and obj.object_id == object_id
            for obj in objects
        )

    def is_high_confidence(
        self,
        threshold: float = 0.85,
    ) -> bool:
        """
        Check whether the event meets the supplied confidence threshold.
        """

        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                "threshold must be between 0 and 1."
            )

        return (
            self.status == EventStatus.VALIDATED
            and self.confidence >= threshold
        )

    def get_duration(self) -> Optional[float]:
        """
        Return explicit or derived action duration.
        """

        if self.duration_seconds is not None:
            return self.duration_seconds

        if (
            self.start_timestamp is not None
            and self.end_timestamp is not None
        ):
            return (
                self.end_timestamp
                - self.start_timestamp
            ).total_seconds()

        return None
