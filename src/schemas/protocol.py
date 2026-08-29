"""
Protocol schemas for BAS-HAR.

The protocol layer determines whether an observed ActionEvent
is valid according to the configured experiment procedure.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import Field, model_validator

from .action import ActionType
from .common import SchemaBase


# ============================================================================
# PROTOCOL STATUS
# ============================================================================

class ProtocolStatus(str, Enum):
    """
    Result of protocol validation.
    """

    VALID = "valid"
    INVALID = "invalid"
    UNCERTAIN = "uncertain"


# ============================================================================
# STEP STATUS
# ============================================================================

class StepStatus(str, Enum):
    """
    Runtime status of a protocol step.
    """

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


# ============================================================================
# PROTOCOL STEP
# ============================================================================

class ProtocolStep(SchemaBase):
    """
    Definition of one experiment step.
    """

    id: str = Field(
        min_length=1,
    )

    name: str = Field(
        min_length=1,
    )

    action: ActionType

    object_id: Optional[str] = None

    tool_id: Optional[str] = None

    allowed_zones: List[str] = Field(
        default_factory=list,
    )

    allowed_next: List[str] = Field(
        default_factory=list,
    )

    preconditions: List[str] = Field(
        default_factory=list,
    )

    min_duration_seconds: Optional[float] = Field(
        default=None,
        ge=0.0,
    )

    max_duration_seconds: Optional[float] = Field(
        default=None,
        ge=0.0,
    )

    on_failure: Optional[str] = None

    @model_validator(mode="after")
    def validate_duration_range(self) -> "ProtocolStep":

        if (
            self.min_duration_seconds is not None
            and self.max_duration_seconds is not None
            and self.min_duration_seconds
            > self.max_duration_seconds
        ):
            raise ValueError(
                "min_duration_seconds cannot exceed "
                "max_duration_seconds."
            )

        return self


# ============================================================================
# EXPERIMENT PROTOCOL
# ============================================================================

class ExperimentProtocol(SchemaBase):
    """
    Complete experiment definition.
    """

    experiment_id: str = Field(
        min_length=1,
    )

    version: str = Field(
        default="1.0",
        min_length=1,
    )

    name: str = Field(
        min_length=1,
    )

    initial_step_id: str = Field(
        min_length=1,
    )

    steps: List[ProtocolStep] = Field(
        min_length=1,
    )

    metadata: Dict[str, str] = Field(
        default_factory=dict,
    )

    @model_validator(mode="after")
    def validate_graph(self) -> "ExperimentProtocol":

        step_ids = {
            step.id
            for step in self.steps
        }

        if self.initial_step_id not in step_ids:
            raise ValueError(
                "initial_step_id must reference an existing step."
            )

        for step in self.steps:

            for next_step in step.allowed_next:

                if next_step not in step_ids:
                    raise ValueError(
                        f"Step '{step.id}' references unknown "
                        f"next step '{next_step}'."
                    )

            if (
                step.on_failure is not None
                and step.on_failure not in step_ids
            ):
                raise ValueError(
                    f"Step '{step.id}' references unknown "
                    f"failure step '{step.on_failure}'."
                )

        return self


# ============================================================================
# VALIDATION RESULT
# ============================================================================

class ValidationResult(SchemaBase):
    """
    Output of the protocol engine.

    This is where the system decides whether the ActionEvent
    conforms to the experiment procedure.
    """

    status: ProtocolStatus

    current_step_id: str

    expected_action: ActionType

    observed_action: ActionType

    expected_object_id: Optional[str] = None

    observed_object_id: Optional[str] = None

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    message: str = Field(
        min_length=1,
    )

    next_step_id: Optional[str] = None

    protocol_can_advance: bool = False

    recovery_step_id: Optional[str] = None

    violation_code: Optional[str] = None