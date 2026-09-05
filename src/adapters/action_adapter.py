# File: src/adapters/action_adapter.py
from typing import Dict, Any, Optional, List
from src.interfaces.action_recognizer import ActionRecognizerInterface
from src.schemas.action import ActionEvent, ActionType
from src.schemas.track import Track
from src.schemas.spatial import SpatialState
from src.action.recognizer import ActionRecognizer


class ActionAdapter:
    """
    Adapter converting M2 ActionEvent domain objects into standardized Protocol Engine payloads.
    """

    # Mapping M2 ActionType to experiment protocol step IDs
    ACTION_TO_STEP_MAP: Dict[ActionType, str] = {
        ActionType.IDENTIFY: "S1",
        ActionType.PICK: "S2",
        ActionType.OPEN: "S3",
        ActionType.TRANSFER: "S4",
        ActionType.SEAL: "S5",
        ActionType.PLACE: "S6"
    }

    @classmethod
    def to_protocol_event(cls, action_event: ActionEvent) -> Dict[str, Any]:
        """
        Converts an ActionEvent to the dictionary format expected by ProtocolStateMachine.
        """
        step_id = cls.ACTION_TO_STEP_MAP.get(action_event.action, "UNKNOWN")
        return {
            "step_id": step_id,
            "action": action_event.action.value,
            "object": action_event.object,
            "actor": action_event.actor,
            "timestamp": action_event.timestamp,
            "confidence": action_event.confidence,
            "rack_zone": action_event.rack_zone,
            "status": action_event.status.value,
            "metadata": action_event.metadata
        }


class ActionRecognizerAdapter(ActionRecognizerInterface):
    """
    Adapter wrapping ActionRecognizer to satisfy the central BASPipeline ActionRecognizerInterface.
    """

    def __init__(self, recognizer: Optional[ActionRecognizer] = None):
        self._recognizer = recognizer or ActionRecognizer()
        self._last_event: Optional[ActionEvent] = None

    def recognize(
        self,
        tracks: List[Track],
        spatial_state: Optional[SpatialState] = None
    ) -> Optional[ActionEvent]:
        """
        Recognizes action from tracks and temporal buffer.
        """
        # When called in pipeline, returns the last confirmed action event
        return self._last_event

    def submit_confirmed_action(self, event: ActionEvent) -> None:
        """Sets the current confirmed action."""
        self._last_event = event

    def reset(self) -> None:
        """Resets recognizer state."""
        self._recognizer.reset()
        self._last_event = None

    def name(self) -> str:
        return "ActionRecognizerAdapter"
