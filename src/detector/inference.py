# File: src/detector/inference.py
import logging
from pathlib import Path
from typing import List, Optional, Union
import numpy as np

from src.schemas.detection import BoundingBox, Detection

logger = logging.getLogger(__name__)


class YOLOObjectDetector:
    """
    Lightweight YOLO Object Detector for on-board experiment objects.
    Supports Ultralytics PyTorch/ONNX models with fallback simulation when weights are missing.
    """

    DEFAULT_CLASSES = ["astronaut", "tube_A", "tube_B", "pipette", "cap", "tray", "rack"]

    def __init__(self, model_path: Optional[Union[str, Path]] = None, conf_threshold: float = 0.25):
        self.model_path = Path(model_path) if model_path else None
        self.conf_threshold = conf_threshold
        self.model = None
        self.is_mock = False

        self._init_model()

    def _init_model(self) -> None:
        """Initializes Ultralytics YOLO model or enables fallback mode if unavailable."""
        if self.model_path and self.model_path.exists():
            try:
                from ultralytics import YOLO
                self.model = YOLO(str(self.model_path))
                logger.info(f"Loaded YOLO model from {self.model_path}")
                return
            except Exception as e:
                logger.warning(f"Failed to load YOLO model from {self.model_path}: {e}")

        logger.info("YOLOObjectDetector running in simulation/mock fallback mode.")
        self.is_mock = True

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Runs object detection on an image frame.

        Args:
            frame: OpenCV BGR image array (H, W, 3).

        Returns:
            List of typed Detection objects.
        """
        if frame is None or frame.size == 0:
            return []

        h, w = frame.shape[:2]

        if not self.is_mock and self.model is not None:
            try:
                results = self.model(frame, conf=self.conf_threshold, verbose=False)
                detections: List[Detection] = []
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        cls_name = self.model.names.get(cls_id, f"object_{cls_id}")
                        conf = float(box.conf[0].item())
                        xyxy = box.xyxy[0].tolist()

                        detections.append(Detection(
                            class_name=cls_name,
                            confidence=round(conf, 3),
                            bbox=BoundingBox(
                                x1=round(xyxy[0], 1),
                                y1=round(xyxy[1], 1),
                                x2=round(xyxy[2], 1),
                                y2=round(xyxy[3], 1)
                            )
                        ))
                return detections
            except Exception as e:
                logger.error(f"Error during YOLO model inference: {e}. Falling back to simulation.")

        # Fallback simulation detections for BAS experiment objects
        return [
            Detection(
                class_name="astronaut",
                confidence=0.96,
                bbox=BoundingBox(x1=int(w * 0.1), y1=int(h * 0.1), x2=int(w * 0.9), y2=int(h * 0.9))
            ),
            Detection(
                class_name="tube_A",
                confidence=0.91,
                bbox=BoundingBox(x1=int(w * 0.4), y1=int(h * 0.45), x2=int(w * 0.48), y2=int(h * 0.7))
            ),
            Detection(
                class_name="rack",
                confidence=0.94,
                bbox=BoundingBox(x1=int(w * 0.6), y1=int(h * 0.5), x2=int(w * 0.85), y2=int(h * 0.8))
            )
        ]
