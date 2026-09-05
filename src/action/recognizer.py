# File: src/action/recognizer.py
import logging
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

from src.schemas.action import ActionEvent
from src.detector.inference import YOLOObjectDetector
from src.detector.pose import MediaPipePoseEstimator
from src.tracker.track import ObjectTracker
from src.tracker.identity import TrackHistoryManager
from src.spatial.spatial_reasoner import SpatialReasoner
from src.action.action_rules import HandObjectInteractionDetector
from src.action.temporal import TemporalActionBuffer

logger = logging.getLogger(__name__)


class ActionRecognizer:
    """
    M2 Master Perception & Action Recognition Engine.
    Executes the full pipeline:
      Camera Frame -> YOLO Detection -> Pose/Hand Landmarks -> Tracking -> Spatial Context -> Temporal Buffer -> ActionEvents.
    """

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        detector_model_path: Optional[str] = None,
        action_cooldown: float = 2.0
    ):
        self.frame_width = frame_width
        self.frame_height = frame_height

        # Initialize core pipeline modules
        self.detector = YOLOObjectDetector(model_path=detector_model_path)
        self.pose_estimator = MediaPipePoseEstimator()
        self.tracker = ObjectTracker(iou_threshold=0.15, max_center_distance=220.0)
        self.history = TrackHistoryManager(history_length=35)
        self.spatial = SpatialReasoner(frame_width=frame_width, frame_height=frame_height)
        self.interaction_detector = HandObjectInteractionDetector(
            contact_threshold=65.0,
            approach_threshold=140.0,
            spatial_reasoner=self.spatial
        )
        self.temporal_buffer = TemporalActionBuffer(
            window_size=30,
            action_cooldown_seconds=action_cooldown
        )

    def process_frame(
        self,
        frame: np.ndarray,
        timestamp: float
    ) -> Tuple[List[ActionEvent], Dict[str, Any]]:
        """
        Processes a single video frame through the complete M2 AI perception pipeline.

        Args:
            frame: OpenCV BGR image array (H, W, 3).
            timestamp: Frame capture timestamp in seconds.

        Returns:
            Tuple of:
              - List of newly confirmed ActionEvent objects for this frame.
              - Telemetry dictionary containing active tracks, landmarks, and interaction states for UI/debugging.
        """
        if frame is None or frame.size == 0:
            return [], {}

        # Stage 1: Object Detection & Pose Landmarks
        detections = self.detector.detect(frame)
        pose_landmarks = self.pose_estimator.estimate_pose(frame)

        # Extract hand & wrist landmarks
        hand_landmarks = [
            lm for lm in pose_landmarks
            if "wrist" in lm.name or "hand" in lm.name
        ]

        # Stage 2: Persistent Multi-Object Tracking
        active_tracks = self.tracker.update(detections)
        self.history.record_tracks(active_tracks)

        # Stage 3: Spatial Rack Context & Hand-Object Proximity
        active_tracks = self.spatial.update_object_zones(active_tracks)
        interactions = self.interaction_detector.evaluate_interactions(
            tracks=active_tracks,
            hand_landmarks=hand_landmarks,
            history=self.history
        )

        # Stage 4: Temporal Sliding Window Action Recognition
        confirmed_actions = self.temporal_buffer.update(interactions, timestamp)

        # Build telemetry payload
        telemetry = {
            "timestamp": timestamp,
            "detections_count": len(detections),
            "tracks": active_tracks,
            "landmarks": pose_landmarks,
            "hand_landmarks": hand_landmarks,
            "interactions": interactions,
            "confirmed_actions": confirmed_actions
        }

        return confirmed_actions, telemetry

    def reset(self) -> None:
        """Resets all internal tracking and temporal action buffers."""
        self.tracker.reset()
        self.history.reset()
        self.temporal_buffer.reset()
        logger.info("ActionRecognizer pipeline reset.")

    def close(self) -> None:
        """Releases underlying model resources."""
        self.pose_estimator.close()
