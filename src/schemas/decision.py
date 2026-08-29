"""
Decision schemas for BAS-HAR.

Protocol validation determines whether an action is valid.
Decision logic determines how the system should respond.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import Field

from .common import SchemaBase


class DecisionStatus(str, Enum):
    """
    Runtime action the system should take.
    """

    PROCEED = "proceed"
    ALERT = "alert"
    VERIFY = "verify"
    RECOVER = "recover"
    PAUSE = "pause"
    STOP = "stop"


class DecisionReason(str, Enum):
    """
    Reason behind a runtime decision.
    """

    VALID_STEP = "valid_step"
    WRONG_SEQUENCE = "wrong_sequence"
    LOW_CONFIDENCE = "low_confidence"
    MISSING_EVIDENCE = "missing_evidence"
    WRONG_OBJECT = "wrong_object"
    WRONG_TOOL = "wrong_tool"
    WRONG_ZONE = "wrong_zone"
    TIMEOUT = "timeout"
    SYSTEM_ERROR = "system_error"
    UNKNOWN = "unknown"


class Decision(SchemaBase):
    """
    Final runtime decision consumed by:
        UI
        TTS
        Logger
        Evidence subsystem
    """

    decision_id: str = Field(
        min_length=1,
    )

    status: DecisionStatus

    reason: DecisionReason

    message: str = Field(
        min_length=1,
    )

    current_step_id: Optional[str] = None

    next_step_id: Optional[str] = None

    recovery_step_id: Optional[str] = None

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    requires_attention: bool = False

    protocol_advances: bool = False

    should_speak: bool = False

    voice_message: Optional[str] = None