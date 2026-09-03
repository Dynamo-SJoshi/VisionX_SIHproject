"""
BAS-HAR central integration pipeline.

Architecture:

    Camera
        ↓
    Detector
        ↓
    Tracker
        ↓
    Spatial Reasoning (optional)
        ↓
    Action Recognition
        ↓
    Protocol Validation
        ↓
    Decision Engine
        ↓
    System Event
        ↓
    Logger

M1 owns this orchestration layer.

Important design rule:
    The pipeline coordinates modules.
    It does NOT implement the internals of those modules.
"""

from __future__ import annotations

from typing import Any, Optional

from src.interfaces.action_recognizer import ActionRecognizerInterface
from src.interfaces.camera import CameraInterface
from src.interfaces.decision_engine import DecisionEngineInterface
from src.interfaces.detector import DetectorInterface
from src.interfaces.logger import LoggerInterface
from src.interfaces.protocol_engine import ProtocolEngineInterface
from src.interfaces.tracker import TrackerInterface

from src.schemas.action import ActionEvent
from src.schemas.decision import Decision
from src.schemas.events import (
    SystemEvent,
    SystemEventType,
)
from src.schemas.spatial import SpatialState


class BASPipeline:
    """
    Central BAS-HAR orchestration pipeline.

    The pipeline is intentionally independent of concrete implementations
    such as YOLO, OpenCV, ByteTrack, a particular protocol implementation,
    or Streamlit.

    Every subsystem communicates through interfaces and schemas.
    """

    def __init__(
        self,
        camera: CameraInterface,
        detector: DetectorInterface,
        tracker: TrackerInterface,
        action_recognizer: ActionRecognizerInterface,
        protocol_engine: ProtocolEngineInterface,
        decision_engine: DecisionEngineInterface,
        logger: LoggerInterface,
        spatial_reasoner: Optional[Any] = None,
    ) -> None:
        """
        Initialize the BAS-HAR pipeline.

        Args:
            camera:
                Camera/video source.

            detector:
                Object/person detector.

            tracker:
                Persistent object/person tracker.

            action_recognizer:
                Converts tracks into semantic ActionEvents.

            protocol_engine:
                Validates ActionEvents against the experiment protocol.

            decision_engine:
                Converts ValidationResult into a runtime Decision.

            logger:
                Persists SystemEvents.

            spatial_reasoner:
                Optional spatial reasoning implementation.
                It should expose:
                    update(tracks) -> SpatialState
        """

        self.camera = camera
        self.detector = detector
        self.tracker = tracker
        self.action_recognizer = action_recognizer
        self.protocol_engine = protocol_engine
        self.decision_engine = decision_engine
        self.logger = logger

        # Optional until the spatial subsystem is implemented.
        self.spatial_reasoner = spatial_reasoner

        # Runtime state.
        self.frame_count: int = 0

        self.last_action: Optional[ActionEvent] = None
        self.last_decision: Optional[Decision] = None
        self.last_spatial_state: Optional[SpatialState] = None

    # ======================================================================
    # MAIN FRAME PROCESSING
    # ======================================================================

    def process_frame(
        self,
        frame: Any,
    ) -> Optional[Decision]:
        """
        Process one video frame through the complete BAS-HAR pipeline.

        Flow:

            frame
                ↓
            detections
                ↓
            tracks
                ↓
            spatial state
                ↓
            action event
                ↓
            validation result
                ↓
            decision
                ↓
            logging

        Returns:
            Decision:
                When a semantic action is recognized and processed.

            None:
                When there is no action event in this frame.
        """

        self.frame_count += 1

        print(
            f"\n========== FRAME {self.frame_count} =========="
        )

        # ------------------------------------------------------------------
        # 1. PERCEPTION
        # ------------------------------------------------------------------

        detections = self.detector.detect(frame)

        print(
            f"[PIPELINE] Detections: {len(detections)}"
        )

        # ------------------------------------------------------------------
        # 2. TRACKING
        # ------------------------------------------------------------------

        tracks = self.tracker.update(detections)

        print(
            f"[PIPELINE] Tracks: {len(tracks)}"
        )

        # ------------------------------------------------------------------
        # 3. OPTIONAL SPATIAL REASONING
        # ------------------------------------------------------------------

        spatial_state: Optional[SpatialState] = None

        if self.spatial_reasoner is not None:

            spatial_state = self.spatial_reasoner.update(
                tracks
            )

            self.last_spatial_state = spatial_state

            print(
                "[PIPELINE] Spatial state updated."
            )

        # ------------------------------------------------------------------
        # 4. ACTION RECOGNITION
        # ------------------------------------------------------------------

        action = self.action_recognizer.recognize(
            tracks=tracks,
            spatial_state=spatial_state,
        )

        # It is completely normal for a frame to contain no completed
        # semantic action.
        if action is None:

            print(
                "[PIPELINE] No semantic action detected."
            )

            return None

        self.last_action = action

        print(
            f"[PIPELINE] Action: {action.action}"
        )

        print(
            f"[PIPELINE] Action confidence: "
            f"{action.confidence:.2f}"
        )

        print(
            f"[PIPELINE] Action status: "
            f"{action.status}"
        )

        # ------------------------------------------------------------------
        # 5. PROTOCOL VALIDATION
        # ------------------------------------------------------------------

        validation = self.protocol_engine.validate(
            action
        )

        print(
            f"[PIPELINE] Protocol status: "
            f"{validation.status}"
        )

        # ------------------------------------------------------------------
        # 6. DECISION
        # ------------------------------------------------------------------

        decision = self.decision_engine.evaluate(
            validation
        )

        self.last_decision = decision

        print(
            f"[PIPELINE] Decision: "
            f"{decision.status}"
        )

        print(
            f"[PIPELINE] Message: "
            f"{decision.message}"
        )

        # ------------------------------------------------------------------
        # 7. SYSTEM EVENT / LOGGING
        # ------------------------------------------------------------------

        system_event = SystemEvent(
            event_id=f"evt_{action.event_id}",

            event_type=SystemEventType.DECISION_CREATED,

            timestamp=action.timestamp,

            session_id=action.session_id,

            message=decision.message,

            actor_id=action.actor_id,

            action_event_id=action.event_id,

            decision_id=decision.decision_id,

            step_id=validation.current_step_id,

            confidence=decision.confidence,

            data={
                "action": action.action,
                "action_status": action.status,
                "protocol_status": validation.status,
                "decision_status": decision.status,
                "expected_action": validation.expected_action,
                "observed_action": validation.observed_action,
                "next_step_id": validation.next_step_id,
                "recovery_step_id": validation.recovery_step_id,
                "violation_code": validation.violation_code,
            },
        )

        self.logger.log(system_event)

        print(
            "[PIPELINE] System event logged."
        )

        return decision

    # ======================================================================
    # CAMERA LIFECYCLE
    # ======================================================================

    def start(self) -> None:
        """
        Start the camera/video source.
        """

        self.camera.start()

    def stop(self) -> None:
        """
        Stop the camera and flush pending log data.
        """

        try:
            self.camera.stop()
        finally:
            self.logger.flush()

    # ======================================================================
    # PIPELINE RESET
    # ======================================================================

    def reset(self) -> None:
        """
        Reset all stateful pipeline components.

        This should normally be called before starting a new experiment
        session.
        """

        self.tracker.reset()

        self.action_recognizer.reset()

        self.protocol_engine.reset()

        self.decision_engine.reset()

        self.frame_count = 0

        self.last_action = None
        self.last_decision = None
        self.last_spatial_state = None

    # ======================================================================
    # STATUS ACCESSORS
    # ======================================================================

    def get_last_action(
        self,
    ) -> Optional[ActionEvent]:
        """
        Return the most recently recognized action event.
        """

        return self.last_action

    def get_last_decision(
        self,
    ) -> Optional[Decision]:
        """
        Return the most recent runtime decision.
        """

        return self.last_decision

    def get_last_spatial_state(
        self,
    ) -> Optional[SpatialState]:
        """
        Return the most recent spatial state, if spatial reasoning
        is enabled.
        """

        return self.last_spatial_state

    def get_frame_count(self) -> int:
        """
        Return the number of processed frames.
        """

        return self.frame_count