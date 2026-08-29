
from typing import List
from src.interfaces.action_recognizer import ActionRecognizerInterface
from src.schemas.track import Track
from src.schemas.action import ActionEvent, ActionType
from src.schemas.common import utc_now

class MockActionRecognizer(ActionRecognizerInterface):
    def recognize(self, tracks: List[Track]) -> ActionEvent:
        print("[ACTION] Recognizing action")
        
        return ActionEvent(
            event_id="act_mock_01",
            actor_id="astronaut_01",
            action=ActionType.TRANSFER,
            object_id="tube",
            confidence=0.94,
            timestamp=utc_now()
        )