from typing import List
from src.interfaces.detector import DetectorInterface
from src.schemas.detection import Detection
from src.schemas.common import utc_now

class MockDetector(DetectorInterface):
    def detect(self, frame: any) -> List[Detection]:
        print("[DETECTOR] Processing frame")
        
        return [
            Detection(
                detection_id="det_mock_01",
                label="tube",
                confidence=0.95,
                bbox=(100, 120, 200, 250),
                frame_id=frame.get("frame_id", 0),
                source_camera="CAM-MOCK",
                timestamp=utc_now()
            )
        ]