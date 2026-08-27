# File: src/ui/backend.py
import logging
import os
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from src.camera.capture import CameraCapture
from src.detector.objects import detect_objects
from src.detector.pose import estimate_pose
from src.tracker.track import ObjectTracker
from src.protocol.graph import ProtocolGraph
from src.protocol.state_machine import ProtocolStateMachine
from src.logger.event_logger import EventLogger
from src.tts.offline_tts import OfflineTTS

logger = logging.getLogger(__name__)

# FastAPI Application instance
app = FastAPI(
    title="BAS HAR Assistant Backend API",
    description="Offline REST API for On-board Astronaut HAR & Protocol Monitoring",
    version="1.0.0"
)

# Global Manager Class holding application state
class AppState:
    def __init__(self, config_path: str = "data/configs/sample_transfer_v1.json"):
        self.config_path = Path(config_path)
        self.graph = ProtocolGraph(self.config_path)
        self.state_machine = ProtocolStateMachine(self.graph)
        self.logger = EventLogger(log_dir="logs", experiment_id=self.graph.experiment_id)
        self.tts = OfflineTTS(enabled=True)
        self.camera = CameraCapture(source=0)
        self.tracker = ObjectTracker()

        self.last_confidence: float = 0.95
        self.last_alert: str = "OK"
        self.last_message: str = "System initialized."
        self.is_running: bool = False
        self.pipeline_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start_pipeline(self) -> None:
        """Starts the background camera and HAR processing pipeline thread."""
        if not self.is_running:
            self.is_running = True
            self.pipeline_thread = threading.Thread(target=self._run_loop, daemon=True)
            self.pipeline_thread.start()
            logger.info("Background processing pipeline thread started.")

    def stop_pipeline(self) -> None:
        """Stops the background processing thread."""
        self.is_running = False
        if self.tts:
            self.tts.stop()
        if self.camera:
            self.camera.release()

    def _run_loop(self) -> None:
        """Continuous background execution loop reading frames and running AI pipeline stubs."""
        while self.is_running:
            try:
                # 1. Read Frame
                frame, timestamp = self.camera.read_frame()

                # 2. Run Detector & Tracker stubs
                detections = detect_objects(frame)
                pose_data = estimate_pose(frame)
                tracked_objs = self.tracker.update(detections)

                # 3. Simulate processing time delay
                time.sleep(0.2)

            except Exception as e:
                logger.error(f"Error in background processing loop: {e}")
                time.sleep(0.5)

    def trigger_step_event(self, step_id: str, confidence: float = 0.95) -> Dict[str, Any]:
        """Manually trigger an observed step event and update protocol state machine."""
        with self._lock:
            event_input = {"step_id": step_id, "confidence": confidence}
            result = self.state_machine.process_observed_step(event_input)

            self.last_confidence = confidence
            self.last_alert = result["alert_type"]
            self.last_message = result["message"]

            # Log Event
            current_step_obj = self.state_machine.get_current_step()
            curr_id = current_step_obj.id if current_step_obj else step_id
            self.logger.log_event(
                step_id=curr_id,
                event_type="STEP_TRANSITION",
                alert_type=result["alert_type"],
                confidence=confidence,
                metadata={"message": result["message"], "observed_step": step_id}
            )

            # Announce via TTS
            alert = result["alert_type"]
            if alert == "OK":
                self.tts.speak(f"Step verified: {curr_id}.")
            elif alert == "SKIPPED":
                self.tts.speak(f"Alert: Step skipped! Expected step was {result['next_step']}.")
            elif alert == "WRONG_ORDER":
                self.tts.speak(f"Alert: Wrong order sequence for step {step_id}.")
            elif alert == "COMPLETED":
                self.tts.speak("Experiment protocol completed successfully.")
            elif alert == "UNEXPECTED":
                self.tts.speak(f"Alert: Unexpected step {step_id}.")

            return result

    def get_status_summary(self) -> Dict[str, Any]:
        """Returns current status summary for REST endpoint."""
        with self._lock:
            curr_step = self.state_machine.get_current_step()
            next_allowed = self.state_machine.get_next_step_suggestion()

            return {
                "experiment_id": self.graph.experiment_id,
                "current_step_id": curr_step.id if curr_step else "UNKNOWN",
                "current_step_name": curr_step.name if curr_step else "",
                "current_step_description": curr_step.description if curr_step else "",
                "next_allowed_steps": next_allowed,
                "last_alert": self.last_alert,
                "last_message": self.last_message,
                "confidence": self.last_confidence,
                "completed_steps": self.state_machine.completed_steps
            }


# Initialize singleton state manager
state_manager = AppState()


class StepTriggerRequest(BaseModel):
    step_id: str
    confidence: float = 0.95


@app.on_event("startup")
def on_startup():
    state_manager.start_pipeline()


@app.on_event("shutdown")
def on_shutdown():
    state_manager.stop_pipeline()


@app.get("/status")
def get_status():
    """Returns current protocol state, next steps, confidence, and alert status."""
    return state_manager.get_status_summary()


@app.get("/log")
def get_log(limit: int = 20):
    """Returns recent log records."""
    return state_manager.logger.get_recent_events(limit=limit)


@app.post("/reset")
def reset_experiment():
    """Resets the protocol state machine back to step S1."""
    state_manager.state_machine.reset()
    state_manager.last_alert = "OK"
    state_manager.last_message = "Experiment state machine reset to start."
    state_manager.tts.speak("Experiment reset to initial step S1.")
    return {"status": "reset", "current_step": state_manager.state_machine.current_step_id}


@app.post("/trigger_step")
def trigger_step(req: StepTriggerRequest):
    """Manually triggers/simulates an observed step event."""
    result = state_manager.trigger_step_event(req.step_id, req.confidence)
    return result


def start_backend_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Utility to run Uvicorn FastAPI server programmatically."""
    uvicorn.run(app, host=host, port=port, log_level="info")
