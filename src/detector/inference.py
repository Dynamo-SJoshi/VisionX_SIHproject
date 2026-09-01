# File: src/detector/inference.py
import logging
from pathlib import Path
from typing import List, Optional, Union, Dict
import numpy as np

from src.schemas.detection import BoundingBox, Detection

logger = logging.getLogger(__name__)


class YOLOObjectDetector:
    """
    Lightweight YOLO Object Detector for on-board BAS experiment tracking.
    Features aspect-ratio disambiguation for handheld tools and simultaneous multi-object detection.
    """

    # Baseline class mapping from COCO labels to BAS domain objects
    COCO_MAP: Dict[str, str] = {
        "person": "astronaut",
        "bottle": "tube_A",
        "wine glass": "tube_A",
        "cup": "tube_B",
        "bowl": "tube_B",
        "vase": "tube_B",
        "cell phone": "pipette",
        "remote": "pipette",
        "laptop": "rack",
        "book": "tray",
    }

    def __init__(self, model_path: Optional[Union[str, Path]] = None, conf_threshold: float = 0.20):
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
        Runs neural network object detection for simultaneous multi-object tracking.
        Applies geometric aspect-ratio priors to distinguish vertical tubes from flat tools.

        Args:
            frame: OpenCV BGR image array (H, W, 3).

        Returns:
            List of valid BAS Detection objects (supports multiple objects concurrently).
        """
        if frame is None or frame.size == 0 or self.model is None or self.is_mock:
            return []

        try:
            # Sensitive threshold to capture metallic/reflective objects in hand
            results = self.model(frame, conf=0.18, verbose=False)
            raw_detections: List[Detection] = []

            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    raw_name = self.model.names.get(cls_id, f"object_{cls_id}").lower()
                    conf = float(box.conf[0].item())

                    # Filter: Only allow known experiment classes
                    if raw_name not in self.COCO_MAP:
                        continue

                    # Filter confidence per class
                    min_conf = 0.40 if raw_name == "person" else 0.18
                    if conf < min_conf:
                        continue

                    xyxy = box.xyxy[0].tolist()
                    bw = max(1.0, xyxy[2] - xyxy[0])
                    bh = max(1.0, xyxy[3] - xyxy[1])
                    aspect_ratio = bh / bw

                    # Disambiguate cylindrical tubes vs flat tools using geometric aspect ratio
                    if raw_name in ["bottle", "wine glass"]:
                        mapped_name = "tube_A"
                    elif raw_name in ["cell phone", "remote"]:
                        # If a phone/metallic object is held vertically like a tall cylinder (aspect ratio >= 1.7)
                        # and raw confidence is high for bottle, prioritize tube_A
                        if aspect_ratio >= 1.8 and bw < 250:
                            mapped_name = "tube_A"
                        else:
                            mapped_name = "pipette"
                    elif raw_name in ["cup", "bowl", "vase"]:
                        mapped_name = "tube_B"
                    else:
                        mapped_name = self.COCO_MAP[raw_name]

                    raw_detections.append(Detection(
                        class_name=mapped_name,
                        confidence=round(conf, 3),
                        bbox=BoundingBox(
                            x1=round(xyxy[0], 1),
                            y1=round(xyxy[1], 1),
                            x2=round(xyxy[2], 1),
                            y2=round(xyxy[3], 1)
                        )
                    ))

            # Filter duplicate astronaut detections (keep primary astronaut)
            astronaut_dets = [d for d in raw_detections if d.class_name == "astronaut"]
            other_dets = [d for d in raw_detections if d.class_name != "astronaut"]

            final_detections: List[Detection] = []
            if astronaut_dets:
                primary_astronaut = max(astronaut_dets, key=lambda d: d.bbox.area)
                final_detections.append(primary_astronaut)

            # Keep ALL other experiment objects (multiple tubes, pipette, rack, tray)
            final_detections.extend(other_dets)
            return final_detections

        except Exception as e:
            logger.error(f"Error during YOLO model inference: {e}")
            return []
