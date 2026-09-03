# File: src/adapters/action_adapter.py
from typing import Dict, Any, Optional
from src.schemas.action import ActionEvent, ActionType


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
