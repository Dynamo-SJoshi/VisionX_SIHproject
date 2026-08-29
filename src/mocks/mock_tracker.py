from typing import List
from src.interfaces.tracker import TrackerInterface
from src.schemas.detection import Detection
from src.schemas.track import Track
from src.schemas.common import utc_now

class MockTracker(TrackerInterface):
    def update(self, detections: List[Detection]) -> List[Track]:
        print("[TRACKER] Updating tracks")
        tracks = []
        
        for idx, det in enumerate(detections):
            tracks.append(
                Track(
                    track_id=idx + 1,
                    label=det.label,
                    bbox=det.bbox,
                    confidence=det.confidence,
                    frame_id=det.frame_id,
                    timestamp=utc_now(),
                    age_frames=5,
                    is_confirmed=True
                )
            )
            
        return tracks