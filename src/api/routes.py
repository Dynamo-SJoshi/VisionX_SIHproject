"""
FastAPI REST API and Real-Time WebSocket Routes for BAS-HAR Assistant.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

import cv2
import numpy as np
import requests
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles

from src.camera.capture import CameraCapture
from src.detector.inference import YOLOObjectDetector
from src.detector.pose import MediaPipePoseEstimator
from src.tracker.track import ObjectTracker

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
from src.evidence.evidence_manager import EvidenceManager
from src.logger.sqlite_logger import SQLiteLogger
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
sqlite_logger = SQLiteLogger("data/logs/bas_events.db")
evidence_manager = EvidenceManager("data/evidence/snapshots")

camera_capture = CameraCapture(source=0)
detector = YOLOObjectDetector(model_path="yolov8n.pt", conf_threshold=0.30)
tracker = ObjectTracker(iou_threshold=0.25)
pose_estimator = MediaPipePoseEstimator(model_path="yolov8n-pose.pt", conf_threshold=0.50)
# Mount Static Files for Evidence Snapshots
snapshots_dir = Path("data/evidence/snapshots")
snapshots_dir.mkdir(parents=True, exist_ok=True)
app.mount("/evidence_static", StaticFiles(directory=str(snapshots_dir)), name="evidence_static")

# Session State
current_session_id: str = "SESSION_INIT_001"
session_active: bool = False
last_decision_payload: Optional[TelemetryDecisionPayload] = None

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
# BACKGROUND DETECTION LOOP — Runs YOLO continuously in a daemon thread
# HTTP frame endpoints just read from the cached JPEG (instant, no blocking)
# ============================================================================

_frame_lock = threading.Lock()
_latest_annotated_jpeg: bytes = b""
_detection_fps: float = 0.0
_detection_thread_running: bool = True
_active_gesture: Optional[str] = None
_gesture_start_time: float = 0.0
_gesture_cooldown_until: float = 0.0


def _detection_loop() -> None:
    """Continuously captures, annotates and caches the latest JPEG frame."""
    global _latest_annotated_jpeg, _detection_fps, _active_gesture, _gesture_start_time, _gesture_cooldown_until
    fps_timer = time.time()
    frame_count = 0
    while _detection_thread_running:
        try:
            frame, _ = camera_capture.read_frame()
            detections = detector.detect(frame)
            tracks = tracker.update(detections)
            annotated = detector.draw_detections(frame, detections)
            
            # --- Advanced Gesture Recognition ---
            landmarks = pose_estimator.estimate_pose(frame)
            kpts = {lm.name: lm for lm in landmarks}
            
            for lm in landmarks:
                cv2.circle(annotated, (int(lm.x), int(lm.y)), 4, (255, 0, 255), -1)

            current_time = time.time()
            detected_gesture = None
            
            def pt(name): return kpts.get(name)
            
            if current_time > _gesture_cooldown_until:
                lw = pt("left_wrist")
                rw = pt("right_wrist")
                le = pt("left_ear")
                re = pt("right_ear")
                ls = pt("left_shoulder")
                rs = pt("right_shoulder")
                
                # 1. Hands on Head -> Start Session
                if (lw and le and rw and re and
                    abs(lw.y - le.y) < 50 and abs(rw.y - re.y) < 50):
                    detected_gesture = "START_SESSION"
                    
                # Only process other gestures if session is actually active
                elif session_active:
                    # 2. Hands Together (Praying/Clapping) -> Confirm Step
                    #    Checked BEFORE crossed-arms to avoid false stop triggers
                    if (lw and rw and
                          abs(lw.x - rw.x) < 150 and
                          abs(lw.y - rw.y) < 150):
                        detected_gesture = "CONFIRM_STEP"
                        
                    # 3. Crossed Arms -> Stop Session
                    #    Wrists must be far apart (>100px) to distinguish from hands-together
                    elif (lw and rw and ls and rs and
                          abs(lw.x - rw.x) > 100 and
                          abs(lw.x - rs.x) < abs(lw.x - ls.x) and
                          abs(rw.x - ls.x) < abs(rw.x - rs.x)):
                        detected_gesture = "STOP_SESSION"
                        
                    # 4. Right Hand Raised -> Next Step
                    elif (rw and rs and rw.y < rs.y - 30):
                        if not lw or not ls or lw.y > ls.y - 10:
                            detected_gesture = "NEXT_STEP"
                            
                    # 5. Left Hand Raised -> Previous Step
                    elif (lw and ls and lw.y < ls.y - 30):
                        if not rw or not rs or rw.y > rs.y - 10:
                            detected_gesture = "PREV_STEP"

            if detected_gesture:
                if _active_gesture != detected_gesture:
                    _active_gesture = detected_gesture
                    _gesture_start_time = current_time
                else:
                    held_duration = current_time - _gesture_start_time
                    progress = min(1.0, held_duration / 1.5)
                    
                    # Visual feedback
                    cv2.putText(annotated, f"GESTURE: {detected_gesture}", (8, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
                    cv2.rectangle(annotated, (8, 65), (8 + int(200 * progress), 75), (0, 255, 255), -1)
                    cv2.rectangle(annotated, (8, 65), (208, 75), (0, 255, 255), 1)

                    if held_duration >= 1.5:
                        try:
                            if detected_gesture == "NEXT_STEP":
                                requests.post("http://127.0.0.1:8000/api/v1/session/next", timeout=1.0)
                            elif detected_gesture == "PREV_STEP":
                                requests.post("http://127.0.0.1:8000/api/v1/session/prev", timeout=1.0)
                            elif detected_gesture == "STOP_SESSION":
                                requests.post("http://127.0.0.1:8000/api/v1/session/stop", timeout=1.0)
                            elif detected_gesture == "START_SESSION":
                                requests.post("http://127.0.0.1:8000/api/v1/session/start", json={"astronaut_id": "ASTRO_GESTURE", "experiment_id": "sample_transfer_v1"}, timeout=1.0)
                            elif detected_gesture == "CONFIRM_STEP":
                                requests.post("http://127.0.0.1:8000/api/v1/confirm", json={"astronaut_id": "ASTRO_GESTURE", "step_id": "AUTO"}, timeout=1.0)
                            
                            _gesture_cooldown_until = current_time + 2.0
                            _active_gesture = None
                        except Exception as e:
                            print(f"Gesture API error: {e}")
            else:
                _active_gesture = None
            # --------------------------------------------------------

            for trk in tracks:
                if isinstance(trk.bbox, tuple):
                    x1, y1, x2, y2 = trk.bbox
                else:
                    x1, y1, x2, y2 = trk.bbox.x1, trk.bbox.y1, trk.bbox.x2, trk.bbox.y2
                cv2.putText(
                    annotated, f"ID#{trk.track_id}",
                    (int(x1), int(y1 + 15)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1, cv2.LINE_AA,
                )

            # FPS counter
            frame_count += 1
            elapsed = time.time() - fps_timer
            if elapsed >= 1.0:
                _detection_fps = frame_count / elapsed
                fps_timer = time.time()
                frame_count = 0

            cv2.putText(
                annotated, f"FPS: {_detection_fps:.1f}",
                (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 128), 2, cv2.LINE_AA,
            )

            success, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if success:
                with _frame_lock:
                    _latest_annotated_jpeg = buffer.tobytes()
        except Exception:
            time.sleep(0.05)


_bg_thread = threading.Thread(target=_detection_loop, name="DetectionLoop", daemon=True)
_bg_thread.start()


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
        fps=round(_detection_fps, 1),
        status=system_status,
        current_step=current_step_dict,
        next_step=next_step_dict,
        progress_percentage=round(progress_pct, 1),
        protocol_steps=protocol_steps,
        last_decision=last_decision_payload,
        system_health=SystemHealthPayload(session_active=session_active),
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
        "detection_fps": round(_detection_fps, 1),
        "yolo_ready": detector.is_ready(),
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

        telemetry = build_telemetry_payload()
        await ws_manager.broadcast_json(telemetry.model_dump())

        loaded = protocol_engine._protocol
        protocol_name = loaded.name if loaded is not None else "Unknown"
        protocol_version = loaded.version if loaded is not None else "?"

        return {
            "status": "SUCCESS",
            "message": f"Loaded protocol '{protocol_name}' (v{protocol_version})",
            "initial_step": protocol_engine.get_current_step_id(),
        }
    except HTTPException:
        raise  # Let FastAPI handle validation/input errors directly
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
    """Starts a new experiment session and records it in SQLite."""
    global current_session_id, session_active, last_decision_payload
    current_session_id = request.session_id or f"EXP_{int(time.time())}"
    session_active = True
    protocol_engine.reset()
    decision_engine.reset()
    last_decision_payload = None

    # Record session start in SQLite
    sqlite_logger.start_session(
        session_id=current_session_id,
        experiment_id=request.experiment_id or "unknown_experiment",
        start_time=time.time(),
        metadata={"astronaut_id": request.astronaut_id},
    )

    telemetry = build_telemetry_payload()
    await ws_manager.broadcast_json(telemetry.model_dump())

    return {
        "status": "SESSION_STARTED",
        "session_id": current_session_id,
        "experiment_id": request.experiment_id,
    }


@app.post("/api/v1/session/stop")
async def stop_session() -> Dict[str, Any]:
    """Stops the active session and marks it completed in SQLite."""
    global session_active
    session_active = False

    sqlite_logger.stop_session(current_session_id, end_time=time.time())

    return {
        "status": "SESSION_STOPPED",
        "session_id": current_session_id,
    }


@app.post("/api/v1/session/next")
async def force_next_step() -> Dict[str, Any]:
    """Manually force the protocol to advance to the next step."""
    new_step_id = protocol_engine.force_next_step()
    if not new_step_id:
        raise HTTPException(status_code=400, detail="Cannot advance further.")
    
    telemetry = build_telemetry_payload()
    await ws_manager.broadcast_json(telemetry.model_dump())

    return {
        "status": "ADVANCED",
        "current_step_id": new_step_id,
    }


@app.post("/api/v1/session/prev")
async def force_prev_step() -> Dict[str, Any]:
    """Manually force the protocol to revert to the previous step."""
    new_step_id = protocol_engine.force_prev_step()
    if not new_step_id:
        raise HTTPException(status_code=400, detail="No previous steps available.")

    telemetry = build_telemetry_payload()
    await ws_manager.broadcast_json(telemetry.model_dump())

    return {
        "status": "REVERTED",
        "current_step_id": new_step_id,
    }


@app.post("/api/v1/action")
async def ingest_action(action_event: ActionEvent) -> Dict[str, Any]:
    """
    Ingests an ActionEvent from CV/action layer, runs protocol validation + decision evaluation,
    records in SQLite audit log, and streams live telemetry to WebSocket clients.
    """
    global last_decision_payload

    # 1. Protocol Validation (M3)
    validation: ValidationResult = protocol_engine.validate(action_event)

    # 2. Decision Engine Evaluation (M3)
    decision: Decision = decision_engine.evaluate(validation)

    # 3. Evidence Generation (M3)
    evidence_bundle = evidence_manager.capture_for_action(action_event, frame=None)
    evidence_id = evidence_bundle.evidence_id
    snapshot_item = evidence_bundle.items[0] if evidence_bundle.items else None
    snapshot_url = (
        f"/evidence_static/{Path(snapshot_item.snapshot_path).name}"
        if snapshot_item and snapshot_item.snapshot_path
        else None
    )

    # Normalize enums for telemetry
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

    # 4. Store Decision Payload for Telemetry
    last_decision_payload = TelemetryDecisionPayload(
        type=val_status_str,
        action=act_str,
        confidence=round(action_event.confidence, 2),
        rack_zone=action_event.interaction_zone,
        explanation=decision.message,
        voice_message=decision.voice_message,
        evidence_snapshot_url=snapshot_url,
    )

    # 5. Persist to SQLite Audit Log (M3)
    sqlite_logger.log_pipeline_event(
        session_id=current_session_id,
        action=action_event,
        validation=validation,
        decision=decision,
        evidence_id=evidence_id,
        snapshot_path=snapshot_item.snapshot_path if snapshot_item else None,
    )

    # 6. Broadcast live telemetry update to Mission Control
    telemetry = build_telemetry_payload()
    await ws_manager.broadcast_json(telemetry.model_dump())

    return {
        "validation": validation.model_dump(),
        "decision": decision.model_dump(),
        "evidence_id": evidence_id,
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

    manual_event = ActionEvent(
        event_id=f"evt_manual_{uuid.uuid4().hex[:6]}",
        session_id=current_session_id,
        sequence_number=1,
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

    sqlite_logger.log_pipeline_event(
        session_id=current_session_id,
        action=manual_event,
        validation=validation,
        decision=decision,
        evidence_id=None,
        snapshot_path=None,
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
async def export_logs(
    session_id: Optional[str] = None,
    format: str = Query("json", enum=["json", "csv"]),
) -> Any:
    """Exports session audit trail logs from SQLite in JSON or CSV format."""
    sid = session_id or current_session_id
    events = sqlite_logger.get_session_events(sid, limit=1000)

    if format == "csv":
        export_csv_path = Path("data/logs") / f"export_{sid}.csv"
        csv_file = sqlite_logger.export_session_csv(sid, export_csv_path)
        return FileResponse(
            csv_file,
            media_type="text/csv",
            filename=f"session_audit_{sid}.csv",
        )

    return {
        "session_id": sid,
        "total_events": len(events),
        "logs": events,
    }


# ============================================================================
# VIDEO STREAMING ENDPOINTS
# ============================================================================

@app.get("/api/v1/video/feed")
def video_feed():
    """MJPEG streaming endpoint — serves cached annotated frames from background detection loop."""
    def frame_generator():
        while True:
            with _frame_lock:
                jpeg = _latest_annotated_jpeg
            if jpeg:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                )
            time.sleep(0.033)  # cap MJPEG client to ~30 FPS

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/v1/video/frame")
def single_frame() -> Response:
    """
    Returns the latest annotated JPEG from the background detection cache.
    Instant — no blocking YOLO call on the request path.
    """
    with _frame_lock:
        jpeg = _latest_annotated_jpeg

    if not jpeg:
        # Detection loop hasn't produced a frame yet — return a placeholder
        placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            placeholder, "Initializing detector...",
            (140, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2,
        )
        _, buf = cv2.imencode(".jpg", placeholder)
        jpeg = buf.tobytes()

    return Response(content=jpeg, media_type="image/jpeg")


@app.post("/api/v1/video/detect_image")
async def detect_uploaded_image(file: UploadFile = File(...)) -> Response:
    """
    Accepts a multipart-uploaded image (e.g. from browser webcam),
    runs YOLO detection overlay, and returns the annotated JPEG.
    """
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid or unreadable image data.")

    detections = detector.detect(img)
    annotated = detector.draw_detections(img, detections)
    success, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode annotated image.")
    return Response(content=buffer.tobytes(), media_type="image/jpeg")


# ============================================================================
# WEBSOCKET TELEMETRY ENDPOINT
# ============================================================================

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket) -> None:
    """High-frequency WebSocket endpoint for Mission Control live streaming."""
    await ws_manager.connect(websocket)
    try:
        initial_telemetry = build_telemetry_payload()
        await websocket.send_json(initial_telemetry.model_dump())

        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
