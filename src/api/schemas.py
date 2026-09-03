"""
API and Telemetry Pydantic models for BAS-HAR FastAPI server.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProtocolLoadRequest(BaseModel):
    """Request payload to load or hot-swap an experiment configuration."""
    protocol_json: Optional[Dict[str, Any]] = None
    config_file_path: Optional[str] = None


class SessionStartRequest(BaseModel):
    """Request payload to start an experiment session."""
    session_id: Optional[str] = None
    experiment_id: Optional[str] = "sample_transfer_v1"
    astronaut_id: str = "astronaut_01"


class ManualConfirmRequest(BaseModel):
    """Request payload for manual astronaut or operator step confirmation override."""
    step_id: str
    astronaut_id: str = "astronaut_01"
    notes: Optional[str] = None


class TelemetryStepItem(BaseModel):
    """Representation of a single protocol step in the telemetry timeline."""
    id: str
    title: str
    status: str = Field(description="COMPLETED, ACTIVE, PENDING, or FAILED")
    allowed_next: List[str] = Field(default_factory=list)


class TelemetryDecisionPayload(BaseModel):
    """Last decision outcome broadcasted to Mission Control UI."""
    type: str = Field(description="VALID, INVALID, or UNCERTAIN")
    action: str
    confidence: float
    rack_zone: Optional[str] = None
    explanation: str
    voice_message: Optional[str] = None
    evidence_snapshot_url: Optional[str] = None


class SystemHealthPayload(BaseModel):
    """System health status across edge subsystems."""
    camera: str = "CONNECTED"
    edge_inference: str = "OK"
    protocol_engine: str = "ACTIVE"
    fps: float = 30.0


class TelemetryPayload(BaseModel):
    """
    Standard Real-Time Telemetry WebSocket Contract consumed by M5 (Mission Control).
    """
    timestamp: float
    session_id: str
    experiment_name: str
    fps: float
    status: str = Field(description="NORMAL, PROCEDURE_VIOLATION, or VERIFICATION_PENDING")
    current_step: Optional[Dict[str, Any]] = None
    next_step: Optional[Dict[str, Any]] = None
    progress_percentage: float
    protocol_steps: List[TelemetryStepItem] = Field(default_factory=list)
    last_decision: Optional[TelemetryDecisionPayload] = None
    system_health: SystemHealthPayload = Field(default_factory=SystemHealthPayload)
