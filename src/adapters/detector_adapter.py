# File: src/adapters/detector_adapter.py
from typing import List, Any
import numpy as np

from src.interfaces.detector import DetectorInterface
from src.schemas.detection import Detection
from src.detector.inference import YOLOObjectDetector


class YOLODetectorAdapter(DetectorInterface):
    """
    Adapter bridging YOLOObjectDetector to DetectorInterface for the central BASPipeline.
    """

    def __init__(self, detector: YOLOObjectDetector = None):
        self._detector = detector or YOLOObjectDetector()

    def detect(self, frame: Any) -> List[Detection]:
        """Detects objects from input frame."""
        return self._detector.detect(frame)

    def name(self) -> str:
        return "YOLODetectorAdapter"
