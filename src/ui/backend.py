"""
BAS-HAR FastAPI Backend
=======================

This module is the API and runtime-control layer for BAS-HAR.

IMPORTANT ARCHITECTURAL RULE
-----------------------------

FastAPI is responsible for:
    - exposing REST endpoints
    - controlling pipeline lifecycle
    - returning runtime status
    - exposing recent logs
    - providing development/test controls

BASPipeline is responsible for:
    - camera processing
    - detection
    - tracking
    - spatial reasoning
    - action recognition
    - protocol validation
    - decision generation
    - system-event logging

Do NOT duplicate BAS-HAR processing logic inside this file.

Current stage:
    Mock components are used so the complete system can be tested
    before M2/M3/M4 integrate their real implementations.

Later:
    Replace the mock components in AppState with real implementations.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.logger.event_logger import EventLogger

from src.mocks.mock_action import MockActionRecognizer
from src.mocks.mock_camera import MockCamera
from src.mocks.mock_decision import MockDecisionEngine
from src.mocks.mock_detector import MockDetector
from src.mocks.mock_protocol import MockProtocolEngine
from src.mocks.mock_tracker import MockTracker

from src.pipeline.bas_pipeline import BASPipeline

from src.schemas.action import ActionType


# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("bas_har.backend")


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="BAS-HAR Assistant Backend",
    description=(
        "Offline backend for onboard astronaut activity recognition, "
        "experiment protocol validation, decision support, and logging."
    ),
    version="0.1.0",
)


# =============================================================================
# API REQUEST MODELS
# =============================================================================

class RunRequest(BaseModel):
    """
    Request for processing a finite number of frames.

    Primarily used during development and integration testing.
    """

    frames: int = Field(
        default=1,
        ge=1,
        le=1000,
        description="Number of frames to process.",
    )


class SimulateActionRequest(BaseModel):
    """
    Configure the mock action recognizer.

    This is used to test:
        - valid actions
        - incorrect actions
        - uncertain actions
    """

    action: ActionType = Field(
        description="Action that the mock recognizer should emit.",
    )

    confidence: float = Field(
        default=0.94,
        ge=0.0,
        le=1.0,
        description="Confidence assigned to the simulated action.",
    )


# =============================================================================
# APPLICATION STATE
# =============================================================================

class AppState:
    """
    Central application runtime state.

    This class is intentionally responsible for composition and lifecycle,
    not for implementing AI/protocol business logic.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
    ) -> None:

        # ---------------------------------------------------------------------
        # CONFIGURATION
        # ---------------------------------------------------------------------

        self.config_path = self._resolve_config_path(
            config_path
        )

        # ---------------------------------------------------------------------
        # COMPONENTS
        #
        # These are MOCK implementations for the current integration phase.
        # ---------------------------------------------------------------------

        self.camera = MockCamera()

        self.detector = MockDetector()

        self.tracker = MockTracker()

        self.action_recognizer = MockActionRecognizer(
            action=ActionType.TRANSFER,
            confidence=0.94,
        )

        self.protocol_engine = MockProtocolEngine()

        self.decision_engine = MockDecisionEngine()

        self.logger = EventLogger(
            log_dir="logs",
            experiment_id="bas_har",
        )

        # ---------------------------------------------------------------------
        # CENTRAL BAS PIPELINE
        # ---------------------------------------------------------------------

        self.pipeline = BASPipeline(
            camera=self.camera,
            detector=self.detector,
            tracker=self.tracker,
            action_recognizer=self.action_recognizer,
            protocol_engine=self.protocol_engine,
            decision_engine=self.decision_engine,
            logger=self.logger,
        )

        # ---------------------------------------------------------------------
        # RUNTIME STATE
        # ---------------------------------------------------------------------

        self.is_running: bool = False

        self.pipeline_thread: Optional[
            threading.Thread
        ] = None

        self._lock = threading.RLock()

        self._last_error: Optional[str] = None

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    @staticmethod
    def _resolve_config_path(
        config_path: Optional[str],
    ) -> Path:
        """
        Resolve the protocol configuration path.

        Priority:
            1. Explicit constructor argument
            2. BAS_HAR_CONFIG environment variable
            3. Default project config path
        """

        selected_path = (
            config_path
            or os.getenv("BAS_HAR_CONFIG")
            or "data/configs/sample_transfer_v1.json"
        )

        path = Path(selected_path)

        if not path.is_absolute():
            path = Path.cwd() / path

        return path.resolve()

    # =========================================================================
    # PIPELINE LIFECYCLE
    # =========================================================================

    def start_pipeline(self) -> bool:
        """
        Start continuous BAS-HAR processing.

        Returns:
            True:
                Pipeline started successfully.

            False:
                Pipeline was already running.
        """

        with self._lock:

            if self.is_running:

                return False

            self._last_error = None

            self.pipeline.reset()

            self.pipeline.start()

            self.is_running = True

            self.pipeline_thread = threading.Thread(
                target=self._run_loop,
                name="bas-har-pipeline",
                daemon=True,
            )

            self.pipeline_thread.start()

            logger.info(
                "BAS-HAR background pipeline started."
            )

            return True

    def stop_pipeline(self) -> bool:
        """
        Stop continuous BAS-HAR processing.

        Returns:
            True:
                Pipeline was running and has been stopped.

            False:
                Pipeline was already stopped.
        """

        with self._lock:

            if not self.is_running:

                return False

            self.is_running = False

            thread = self.pipeline_thread

        # ---------------------------------------------------------------------
        # Wait outside the lock so the worker can finish normally.
        # ---------------------------------------------------------------------

        if (
            thread is not None
            and thread.is_alive()
        ):

            thread.join(
                timeout=3.0
            )

        with self._lock:

            self.pipeline_thread = None

            try:
                self.pipeline.stop()

            except Exception as exc:

                logger.exception(
                    "Error while stopping pipeline."
                )

                self._last_error = str(exc)

        logger.info(
            "BAS-HAR background pipeline stopped."
        )

        return True

    # =========================================================================
    # BACKGROUND LOOP
    # =========================================================================

    def _run_loop(self) -> None:
        """
        Continuously read frames and delegate processing to BASPipeline.

        IMPORTANT:
            No AI/protocol logic is implemented here.
        """

        while self.is_running:

            try:

                frame = self.camera.read()

                self.pipeline.process_frame(
                    frame
                )

            except Exception as exc:

                logger.exception(
                    "Error in BAS-HAR pipeline loop."
                )

                with self._lock:
                    self._last_error = str(exc)

                # Stop on a fatal pipeline failure instead of spinning
                # indefinitely.
                with self._lock:
                    self.is_running = False

                break

    # =========================================================================
    # FINITE TEST RUN
    # =========================================================================

    def run_frames(
        self,
        frame_count: int,
    ) -> Optional[dict[str, Any]]:
        """
        Process a finite number of frames.

        This method is intended for deterministic development/testing.

        It must not run while the continuous pipeline is active.
        """

        if frame_count < 1:
            raise ValueError(
                "frame_count must be at least 1."
            )

        with self._lock:

            if self.is_running:

                raise RuntimeError(
                    "Cannot run finite frames while "
                    "the continuous pipeline is running."
                )

            self._last_error = None

            self.pipeline.reset()

            self.pipeline.start()

            last_decision = None

            try:

                for _ in range(frame_count):

                    frame = self.camera.read()

                    last_decision = (
                        self.pipeline.process_frame(
                            frame
                        )
                    )

            finally:

                self.pipeline.stop()

            if last_decision is None:

                return None

            return last_decision.model_dump(
                mode="json"
            )

    # =========================================================================
    # RESET
    # =========================================================================

    def reset(self) -> None:
        """
        Reset all stateful pipeline components.
        """

        with self._lock:

            if self.is_running:

                raise RuntimeError(
                    "Stop the pipeline before resetting."
                )

            self.pipeline.reset()

            self.logger.clear_recent_events()

            self._last_error = None

    # =========================================================================
    # STATUS
    # =========================================================================

    def get_status(self) -> dict[str, Any]:
        """
        Return a complete runtime status summary.
        """

        with self._lock:

            action = (
                self.pipeline.get_last_action()
            )

            decision = (
                self.pipeline.get_last_decision()
            )

            current_step = (
                self.protocol_engine.get_current_step_id()
            )

            expected_action = (
                self.protocol_engine.get_expected_action()
            )

            return {
                "service": "BAS-HAR Assistant",
                "status": (
                    "running"
                    if self.is_running
                    else "idle"
                ),
                "pipeline_running": self.is_running,

                "config_path": str(
                    self.config_path
                ),
                "config_exists": (
                    self.config_path.exists()
                ),

                "frames_processed": (
                    self.pipeline.get_frame_count()
                ),

                "current_step_id": current_step,

                "expected_action": expected_action,

                "last_action": (
                    action.model_dump(
                        mode="json"
                    )
                    if action is not None
                    else None
                ),

                "last_decision": (
                    decision.model_dump(
                        mode="json"
                    )
                    if decision is not None
                    else None
                ),

                "last_error": self._last_error,
            }


# =============================================================================
# GLOBAL APPLICATION STATE
# =============================================================================

state = AppState()


# =============================================================================
# ROOT ENDPOINT
# =============================================================================

@app.get("/")
def root() -> dict[str, Any]:
    """
    Basic service information.
    """

    return {
        "service": "BAS-HAR Assistant Backend",
        "status": "running",
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
        "status_endpoint": "/status",
    }


# =============================================================================
# HEALTH ENDPOINT
# =============================================================================

@app.get("/health")
def health() -> dict[str, Any]:
    """
    Basic health/readiness information.
    """

    status = state.get_status()

    return {
        "status": "ok",
        "service": "BAS-HAR Assistant Backend",
        "pipeline_initialized": (
            state.pipeline is not None
        ),
        "pipeline_running": (
            state.is_running
        ),
        "config_available": (
            state.config_path.exists()
        ),
        "last_error": (
            state._last_error
        ),
    }


# =============================================================================
# STATUS ENDPOINT
# =============================================================================

@app.get("/status")
def get_status() -> dict[str, Any]:
    """
    Return current BAS-HAR runtime state.
    """

    return state.get_status()


# =============================================================================
# RUN FINITE NUMBER OF FRAMES
# =============================================================================

@app.post("/run")
def run_pipeline(
    request: RunRequest,
) -> dict[str, Any]:
    """
    Process a finite number of frames.

    Example request:

        {
            "frames": 5
        }
    """

    try:

        decision = state.run_frames(
            request.frames
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Finite pipeline execution failed."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Pipeline execution failed: {exc}"
            ),
        ) from exc

    return {
        "status": "completed",
        "frames_processed": request.frames,
        "decision": decision,
    }


# =============================================================================
# START CONTINUOUS PIPELINE
# =============================================================================

@app.post("/start")
def start_pipeline() -> dict[str, Any]:
    """
    Start continuous camera processing.
    """

    started = state.start_pipeline()

    return {
        "status": (
            "started"
            if started
            else "already_running"
        ),
        "pipeline_running": (
            state.is_running
        ),
    }


# =============================================================================
# STOP CONTINUOUS PIPELINE
# =============================================================================

@app.post("/stop")
def stop_pipeline() -> dict[str, Any]:
    """
    Stop continuous camera processing.
    """

    stopped = state.stop_pipeline()

    return {
        "status": (
            "stopped"
            if stopped
            else "already_stopped"
        ),
        "pipeline_running": (
            state.is_running
        ),
    }


# =============================================================================
# RESET
# =============================================================================

@app.post("/reset")
def reset_pipeline() -> dict[str, Any]:
    """
    Reset experiment/pipeline state.
    """

    try:

        state.reset()

    except RuntimeError as exc:

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Pipeline reset failed."
        )

        raise HTTPException(
            status_code=500,
            detail=f"Reset failed: {exc}",
        ) from exc

    return {
        "status": "reset",
        "current_step_id": (
            state.protocol_engine
            .get_current_step_id()
        ),
        "expected_action": (
            state.protocol_engine
            .get_expected_action()
        ),
    }


# =============================================================================
# SIMULATE ACTION
# =============================================================================

@app.post("/simulate/action")
def simulate_action(
    request: SimulateActionRequest,
) -> dict[str, Any]:
    """
    Configure the mock recognizer.

    Examples:

        Valid:
            TRANSFER + 0.94

        Wrong:
            OPEN + 0.94

        Uncertain:
            TRANSFER + 0.42
    """

    with state._lock:

        state.action_recognizer.set_action(
            request.action
        )

        state.action_recognizer.set_confidence(
            request.confidence
        )

    return {
        "status": "updated",
        "action": request.action,
        "confidence": request.confidence,
    }


# =============================================================================
# RECENT LOGS
# =============================================================================

@app.get("/logs")
def get_logs(
    limit: int = 20,
) -> dict[str, Any]:
    """
    Return recent structured SystemEvents.
    """

    if limit < 1 or limit > 500:

        raise HTTPException(
            status_code=400,
            detail=(
                "limit must be between 1 and 500."
            ),
        )

    try:

        events = state.logger.get_recent_events(
            limit=limit
        )

    except Exception as exc:

        logger.exception(
            "Failed to retrieve logs."
        )

        raise HTTPException(
            status_code=500,
            detail=f"Unable to retrieve logs: {exc}",
        ) from exc

    return {
        "count": len(events),
        "events": events,
    }


# =============================================================================
# LOG FILE INFORMATION
# =============================================================================

@app.get("/logs/files")
def get_log_files() -> dict[str, Any]:
    """
    Return persistent log file locations.
    """

    getter = getattr(
        state.logger,
        "get_log_paths",
        None,
    )

    if getter is None:

        return {
            "available": False,
            "files": {},
        }

    return {
        "available": True,
        "files": getter(),
    }


# =============================================================================
# SERVER START HELPER
# =============================================================================

def start_backend_server(
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """
    Start the FastAPI application programmatically.

    Normally main.py or the uvicorn CLI should start the server.
    """

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    start_backend_server()