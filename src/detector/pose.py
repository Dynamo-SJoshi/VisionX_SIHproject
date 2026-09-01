# File: src/detector/pose.py
import logging
from pathlib import Path
from typing import List, Optional, Union
import numpy as np

from src.schemas.detection import Landmark

logger = logging.getLogger(__name__)


class MediaPipePoseEstimator:
    """
    Real-time Human Pose & Skeleton Estimator using YOLOv8-Pose.
    Extracts 17 body keypoints (nose, eyes, shoulders, elbows, wrists, hips) with high accuracy.
    """

    KEYPOINT_NAMES = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle"
    ]

    def __init__(self, model_path: Optional[Union[str, Path]] = None, conf_threshold: float = 0.40):
        self.conf_threshold = conf_threshold
        self.model = None
        self.is_mock = False

        self._init_model(model_path)

    def _init_model(self, model_path: Optional[Union[str, Path]]) -> None:
        """Initializes YOLOv8-Pose neural network model."""
        try:
            from ultralytics import YOLO
            model_name = str(model_path) if (model_path and Path(model_path).exists()) else "yolov8n-pose.pt"
            logger.info(f"Loading Pose Estimation model: '{model_name}'...")
            self.model = YOLO(model_name)
            logger.info("Successfully loaded YOLOv8-Pose neural network.")
        except Exception as e:
            logger.warning(f"Could not load YOLOv8-Pose model: {e}. Falling back to basic mode.")
            self.is_mock = True

    def estimate_pose(self, frame: np.ndarray) -> List[Landmark]:
        """
        Estimates real body skeletal keypoints from image frame.

        Args:
            frame: OpenCV BGR image array (H, W, 3).

        Returns:
            List of typed Landmark objects with exact pixel coordinates.
        """
        if frame is None or frame.size == 0 or self.model is None or self.is_mock:
            return []

        try:
            results = self.model(frame, conf=self.conf_threshold, verbose=False)
            landmarks: List[Landmark] = []

            for r in results:
                if r.keypoints is None or r.keypoints.xy is None or len(r.keypoints.xy) == 0:
                    continue

                kpts = r.keypoints.xy[0].tolist()  # (17, 2)
                confs = r.keypoints.conf[0].tolist() if (r.keypoints.conf is not None and len(r.keypoints.conf) > 0) else [1.0] * len(kpts)

                for idx, (pt, conf) in enumerate(zip(kpts, confs)):
                    if conf >= 0.3 and (pt[0] > 0 or pt[1] > 0):
                        name = self.KEYPOINT_NAMES[idx] if idx < len(self.KEYPOINT_NAMES) else f"kp_{idx}"
                        landmarks.append(Landmark(
                            name=name,
                            x=round(float(pt[0]), 1),
                            y=round(float(pt[1]), 1),
                            score=round(float(conf), 3)
                        ))

            return landmarks
        except Exception as e:
            logger.error(f"Error during pose estimation: {e}")
            return []

    def close(self) -> None:
        """Releases pose estimator resources."""
        self.model = None
