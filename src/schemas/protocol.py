from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional
from pydantic import Field
from .action import ActionType
from .common import SchemaBase

class ProtocolStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNCERTAIN = "uncertain"

class StepStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"

class ProtocolStep(SchemaBase):
    """A single experiment step."""
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    action: ActionType
    object_id: Optional[str] = None
    tool_id: Optional[str] = None
    allowed_zones: List[str] = Field(default_factory=list)
    allowed_next: List[str] = Field(default_factory=list)
    preconditions: List[str] = Field(default_factory=list)
    min_duration_seconds: Optional[float] = Field(default=None, ge=0.0)
    max_duration_seconds: Optional[float] = Field(default=None, ge=0.0)
    on_failure: Optional[str] = None

class ExperimentProtocol(SchemaBase):
    """Full experiment protocol loaded from JSON."""
    experiment_id: str = Field(min_length=1)
    version: str = Field(min_length=1, default="1.0")
    name: str = Field(min_length=1)
    initial_step_id: str = Field(min_length=1)
    steps: List[ProtocolStep] = Field(min_length=1)
    metadata: Dict[str, str] = Field(default_factory=dict)

class ValidationResult(SchemaBase):
    """Protocol engine output regarding an observed action."""
    status: ProtocolStatus
    current_step_id: str
    expected_action: ActionType
    observed_action: ActionType
    expected_object_id: Optional[str] = None
    observed_object_id: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    message: str = Field(min_length=1)
    next_step_id: Optional[str] = None
    protocol_can_advance: bool = False
    recovery_step_id: Optional[str] = None
    violation_code: Optional[str] = None