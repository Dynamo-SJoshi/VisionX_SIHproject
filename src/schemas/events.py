from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import Field
from .common import SchemaBase

class SystemEventType(str, Enum):
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    CAMERA_STARTED = "camera_started"
    CAMERA_STOPPED = "camera_stopped"
    CAMERA_ERROR = "camera_error"
    FRAME_RECEIVED = "frame_received"
    DETECTION_CREATED = "detection_created"
    TRACK_UPDATED = "track_updated"
    ACTION_DETECTED = "action_detected"
    PROTOCOL_VALIDATED = "protocol_validated"
    DECISION_CREATED = "decision_created"
    ALERT_TRIGGERED = "alert_triggered"
    VERIFICATION_REQUESTED = "verification_requested"
    RECOVERY_REQUESTED = "recovery_requested"
    EVIDENCE_CAPTURED = "evidence_captured"
    TTS_STARTED = "tts_started"
    TTS_COMPLETED = "tts_completed"
    TTS_ERROR = "tts_error"
    SYSTEM_ERROR = "system_error"

class SystemEvent(SchemaBase):
    """Generic event envelope used by logging/API/UI layers."""
    event_id: str = Field(min_length=1)
    event_type: SystemEventType
    timestamp: datetime
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    actor_id: Optional[str] = None
    action_event_id: Optional[str] = None
    decision_id: Optional[str] = None
    step_id: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    data: Dict[str, Any] = Field(default_factory=dict)