# File: src/detector/inference.py
import logging
from pathlib import Path
from typing import List, Optional, Union, Dict
import numpy as np

from src.schemas.detection import BoundingBox, Detection

logger = logging.getLogger(__name__)


class YOLOObjectDetector:
    """
    Lightweight YOLO Object Detector for on-board experiment objects.
    Features class-specific confidence thresholds and expanded COCO-to-BAS domain mapping.
    """

    # Expanded class mapping from COCO labels to BAS domain objects
    COCO_MAP: Dict[str, str] = {
        "person": "astronaut",
        "cell phone": "pipette",
        "remote": "pipette",
        "bottle": "tube_A",
        "cup": "tube_B",
        "wine glass": "tube_A",
        "bowl": "tube_B",
        "book": "tray",
        "laptop": "rack",
        "keyboard": "tray",
    }

    def __init__(self, model_path: Optional[Union[str, Path]] = None, conf_threshold: float = 0.25):
        self.model_path = Path(model_path) if model_path else None
        self.default_conf_threshold = conf_threshold
        self.model = None
        self.is_mock = False

        self._init_model()

    def _init_model(self) -> None:
        """Initializes Ultralytics YOLO neural network model."""
        try:
            from ultralytics import YOLO

            model_name = str(self.model_path) if (self.model_path and self.model_path.exists()) else "yolov8n.pt"
            logger.info(f"Loading YOLO neural network model: '{model_name}'...")
            self.model = YOLO(model_name)
            logger.info(f"Successfully loaded YOLO model: '{model_name}'")
            return
        except Exception as e:
            logger.warning(f"Could not initialize Ultralytics YOLO model: {e}. Running in fallback mode.")
            self.is_mock = True

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Runs neural network object detection on an image frame with adaptive class thresholds.

        Args:
            frame: OpenCV BGR image array (H, W, 3).

        Returns:
            List of typed Detection objects.
        """
        if frame is None or frame.size == 0 or self.model is None or self.is_mock:
            return []

        try:
            # Run inference with base threshold 0.25 to catch small handheld objects
            results = self.model(frame, conf=0.25, verbose=False)
            detections: List[Detection] = []

            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    raw_name = self.model.names.get(cls_id, f"object_{cls_id}").lower()
                    conf = float(box.conf[0].item())

                    # Adaptive threshold: Require higher confidence (0.40) for person to avoid clothing false positives
                    min_conf = 0.40 if raw_name == "person" else 0.25
                    if conf < min_conf:
                        continue

                    # Map to BAS domain label if recognized
                    mapped_name = self.COCO_MAP.get(raw_name, raw_name)
                    xyxy = box.xyxy[0].tolist()

                    detections.append(Detection(
                        class_name=mapped_name,
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
            logger.error(f"Error during YOLO model inference: {e}")
            return []
