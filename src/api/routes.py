"""
FastAPI REST API and Real-Time WebSocket Routes for BAS-HAR Assistant.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import (
    ManualConfirmRequest,
    ProtocolLoadRequest,
    SessionStartRequest,
    SystemHealthPayload,
    TelemetryDecisionPayload,
    TelemetryPayload,
    TelemetryStepItem,
)
from src.api.websocket import ws_manager
from src.decision.engine import DecisionEngine
from src.protocol.engine import ProtocolEngine
from src.schemas.action import ActionEvent, ActionType, EventStatus
from src.schemas.decision import Decision, DecisionStatus
from src.schemas.protocol import (
    ExperimentProtocol,
    ProtocolStatus,
    ValidationResult,
)

# ============================================================================
# FASTAPI APP & STATE INITIALIZATION
# ============================================================================

app = FastAPI(
    title="BAS AI Copilot - Protocol & Backend Engine",
    description="Offline-first Protocol State Machine, 3-State Safety Decision Engine, and Telemetry API.",
    version="1.0.0",
)

# Enable CORS for Mission Control Frontend (Streamlit / React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State Engines
protocol_engine = ProtocolEngine()
decision_engine = DecisionEngine()

# Session State
current_session_id: str = "SESSION_INIT_001"
session_active: bool = False
last_decision_payload: Optional[TelemetryDecisionPayload] = None
session_logs: list[Dict[str, Any]] = []

# Load default protocol on startup
default_config_path = (
    Path(__file__).parent.parent.parent
    / "data"
    / "configs"
    / "sample_transfer_protocol_v1.json"
)
if default_config_path.exists():
    try:
        protocol_engine.load_protocol_from_file(default_config_path)
    except Exception as e:
        print(f"[API] Warning: Could not auto-load default protocol: {e}")


# ============================================================================
# HELPER TO GENERATE TELEMETRY PAYLOAD
# ============================================================================

def build_telemetry_payload() -> TelemetryPayload:
    """Constructs the unified telemetry payload consumed by M5 Mission Control."""
    current_step_obj = protocol_engine.get_current_step()
    completed_steps = protocol_engine.get_completed_steps()
    protocol_steps: list[TelemetryStepItem] = []

    if protocol_engine._protocol:
        total_steps = len(protocol_engine._protocol.steps)
        progress_pct = (
            (len(completed_steps) / total_steps) * 100.0 if total_steps > 0 else 0.0
        )
        experiment_name = protocol_engine._protocol.name

        for step in protocol_engine._protocol.steps:
            if step.id in completed_steps:
                status_str = "COMPLETED"
            elif current_step_obj and step.id == current_step_obj.id:
                status_str = "ACTIVE"
            else:
                status_str = "PENDING"

            protocol_steps.append(
                TelemetryStepItem(
                    id=step.id,
                    title=step.name,
                    status=status_str,
                    allowed_next=step.allowed_next,
                )
            )
    else:
        progress_pct = 0.0
        experiment_name = "No Protocol Loaded"

    # Status indicator mapping
    system_status = "NORMAL"
    if last_decision_payload:
        if last_decision_payload.type == "INVALID":
            system_status = "PROCEDURE_VIOLATION"
        elif last_decision_payload.type == "UNCERTAIN":
            system_status = "VERIFICATION_PENDING"

    current_step_dict = (
        {
            "id": current_step_obj.id,
            "title": current_step_obj.name,
            "expected_action": protocol_engine.get_expected_action(),
            "state": "IN_PROGRESS",
        }
        if current_step_obj
        else None
    )

    allowed_next = protocol_engine.get_allowed_next_steps()
    next_step_dict = (
        {"id": allowed_next[0]}
        if allowed_next and len(allowed_next) > 0
        else {"id": "COMPLETE"}
    )

    return TelemetryPayload(
        timestamp=time.time(),
        session_id=current_session_id,
        experiment_name=experiment_name,
        fps=30.0,
        status=system_status,
        current_step=current_step_dict,
        next_step=next_step_dict,
        progress_percentage=round(progress_pct, 1),
        protocol_steps=protocol_steps,
        last_decision=last_decision_payload,
        system_health=SystemHealthPayload(),
    )


# ============================================================================
# REST ENDPOINTS
# ============================================================================

@app.get("/api/v1/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for edge deployment monitoring."""
    return {
        "status": "HEALTHY",
        "protocol_loaded": protocol_engine._protocol is not None,
        "session_active": session_active,
        "active_ws_clients": len(ws_manager.active_connections),
    }


@app.get("/api/v1/protocol")
async def get_protocol() -> Dict[str, Any]:
    """Returns the currently active protocol graph structure and execution state."""
    if not protocol_engine._protocol:
        return {"status": "NO_PROTOCOL_LOADED"}

    return {
        "protocol": protocol_engine._protocol.model_dump(),
        "current_step_id": protocol_engine.get_current_step_id(),
        "expected_action": protocol_engine.get_expected_action(),
        "allowed_next": protocol_engine.get_allowed_next_steps(),
        "completed_steps": protocol_engine.get_completed_steps(),
    }


@app.post("/api/v1/protocol/load")
async def load_protocol(request: ProtocolLoadRequest) -> Dict[str, Any]:
    """Hot-swaps the active experiment protocol at runtime without restarting."""
    global last_decision_payload

    try:
        if request.protocol_json:
            protocol = ExperimentProtocol.model_validate(request.protocol_json)
            protocol_engine.load_protocol(protocol)
        elif request.config_file_path:
            protocol_engine.load_protocol_from_file(request.config_file_path)
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide either protocol_json or config_file_path.",
            )

        decision_engine.reset()
        last_decision_payload = None

        # Broadcast updated telemetry to all dashboard clients
        telemetry = build_telemetry_payload()
        await ws_manager.broadcast_json(telemetry.model_dump())

        return {
            "status": "SUCCESS",
            "message": f"Loaded protocol '{protocol_engine._protocol.name}' (v{protocol_engine._protocol.version})",
            "initial_step": protocol_engine.get_current_step_id(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load protocol: {str(e)}")


@app.post("/api/v1/protocol/reset")
async def reset_protocol() -> Dict[str, Any]:
    """Resets the active protocol state back to the first step."""
    global last_decision_payload
    protocol_engine.reset()
    decision_engine.reset()
    last_decision_payload = None

    telemetry = build_telemetry_payload()
    await ws_manager.broadcast_json(telemetry.model_dump())

    return {
        "status": "SUCCESS",
        "current_step": protocol_engine.get_current_step_id(),
    }


@app.post("/api/v1/session/start")
async def start_session(request: SessionStartRequest) -> Dict[str, Any]:
    """Starts a new experiment session."""
    global current_session_id, session_active, session_logs, last_decision_payload
    current_session_id = request.session_id or f"EXP_{int(time.time())}"
    session_active = True
    session_logs = []
    protocol_engine.reset()
    decision_engine.reset()
    last_decision_payload = None

    telemetry = build_telemetry_payload()
    await ws_manager.broadcast_json(telemetry.model_dump())

    return {
        "status": "SESSION_STARTED",
        "session_id": current_session_id,
        "experiment_id": request.experiment_id,
    }


@app.post("/api/v1/session/stop")
async def stop_session() -> Dict[str, Any]:
    """Stops the active session."""
    global session_active
    session_active = False

    return {
        "status": "SESSION_STOPPED",
        "session_id": current_session_id,
        "total_log_entries": len(session_logs),
    }


@app.post("/api/v1/action")
async def ingest_action(action_event: ActionEvent) -> Dict[str, Any]:
    """
    Ingests an observed ActionEvent from CV/action layer, evaluates via Protocol & Decision engines,
    updates telemetry, and broadcasts to WebSocket clients.
    """
    global last_decision_payload

    # 1. Protocol Validation (M3)
    validation: ValidationResult = protocol_engine.validate(action_event)

    # 2. Decision Engine Evaluation (M3)
    decision: Decision = decision_engine.evaluate(validation)

    # Normalize enum/strings for telemetry
    val_status_str = (
        validation.status.value.upper()
        if hasattr(validation.status, "value")
        else str(validation.status).upper()
    )
    act_str = (
        action_event.action.value
        if hasattr(action_event.action, "value")
        else str(action_event.action)
    )

    # 3. Store Decision Payload for Telemetry
    last_decision_payload = TelemetryDecisionPayload(
        type=val_status_str,
        action=act_str,
        confidence=round(action_event.confidence, 2),
        rack_zone=action_event.interaction_zone,
        explanation=decision.message,
        voice_message=decision.voice_message,
        evidence_snapshot_url=None,
    )

    # 4. Log event
    log_entry = {
        "timestamp": time.time(),
        "event_id": action_event.event_id,
        "action": act_str,
        "validation_status": val_status_str.lower(),
        "decision_status": decision.status.value if hasattr(decision.status, "value") else str(decision.status),
        "message": decision.message,
    }
    session_logs.append(log_entry)

    # 5. Broadcast live telemetry update to Mission Control
    telemetry = build_telemetry_payload()
    await ws_manager.broadcast_json(telemetry.model_dump())

    return {
        "validation": validation.model_dump(),
        "decision": decision.model_dump(),
    }


@app.post("/api/v1/confirm")
async def manual_confirm(request: ManualConfirmRequest) -> Dict[str, Any]:
    """
    Operator / Astronaut manual override confirmation.
    Forces advancement when multi-modal verification or occlusion requires manual sign-off.
    """
    global last_decision_payload
    current_step = protocol_engine.get_current_step()
    if not current_step:
        raise HTTPException(status_code=400, detail="No active step to confirm.")

    # Create manual action event
    manual_event = ActionEvent(
        event_id=f"evt_manual_{uuid.uuid4().hex[:6]}",
        session_id=current_session_id,
        sequence_number=len(session_logs) + 1,
        actor_id=request.astronaut_id,
        action=current_step.action,
        confidence=1.0,
        status=EventStatus.VALIDATED,
        target_object=None,
        tool_object=None,
        interaction_zone="MANUAL_CONFIRM",
    )

    validation = protocol_engine.validate(manual_event)
    decision = decision_engine.evaluate(validation)

    last_decision_payload = TelemetryDecisionPayload(
        type="VALID",
        action="manual_confirm",
        confidence=1.0,
        rack_zone="MANUAL",
        explanation=f"Manual operator confirmation accepted for step '{current_step.name}'.",
        voice_message=decision.voice_message,
    )

    telemetry = build_telemetry_payload()
    await ws_manager.broadcast_json(telemetry.model_dump())

    return {
        "status": "CONFIRMED",
        "step_id": request.step_id,
        "new_step": protocol_engine.get_current_step_id(),
    }


@app.get("/api/v1/telemetry")
async def get_telemetry() -> Dict[str, Any]:
    """Returns the latest single-snapshot telemetry state."""
    return build_telemetry_payload().model_dump()


@app.get("/api/v1/logs/export")
async def export_logs() -> Dict[str, Any]:
    """Exports session audit trail logs."""
    return {
        "session_id": current_session_id,
        "total_events": len(session_logs),
        "logs": session_logs,
    }


# ============================================================================
# WEBSOCKET TELEMETRY ENDPOINT
# ============================================================================

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket) -> None:
    """High-frequency WebSocket endpoint for Mission Control live streaming."""
    await ws_manager.connect(websocket)
    try:
        # Send initial snapshot immediately upon connection
        initial_telemetry = build_telemetry_payload()
        await websocket.send_json(initial_telemetry.model_dump())

        # Keep connection open and listen for client pings/messages
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
