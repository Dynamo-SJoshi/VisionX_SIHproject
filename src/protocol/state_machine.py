# File: src/protocol/state_machine.py
from typing import Dict, Any, List, Optional
from .graph import ProtocolGraph, ProtocolStep


class ProtocolStateMachine:
    """State machine tracking and validating astronaut activity step execution."""

    def __init__(self, graph: ProtocolGraph):
        self.graph = graph
        self.current_step_id: str = graph.start_step
        self.completed_steps: List[str] = []
        self.last_alert_type: str = "OK"

    def reset(self) -> None:
        """Resets the state machine back to the initial start step."""
        self.current_step_id = self.graph.start_step
        self.completed_steps = []
        self.last_alert_type = "OK"

    def get_current_step(self) -> Optional[ProtocolStep]:
        """Returns the current step object."""
        return self.graph.get_step(self.current_step_id)

    def get_next_step_suggestion(self) -> List[str]:
        """Returns list of allowed next step IDs."""
        return self.graph.get_allowed_next(self.current_step_id)

    def process_observed_step(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes an observed activity step event (e.g., {"step_id": "S2", "confidence": 0.9}).

        Returns a dictionary containing:
            - current_step: str
            - is_valid_transition: bool
            - next_step: List[str]
            - alert_type: str ("OK", "REPEATED", "SKIPPED", "WRONG_ORDER", "UNEXPECTED", "COMPLETED")
        """
        observed_step_id = event.get("step_id")
        confidence = event.get("confidence", 1.0)

        step_obj = self.graph.get_step(observed_step_id)
        if not step_obj:
            self.last_alert_type = "UNEXPECTED"
            return {
                "current_step": self.current_step_id,
                "is_valid_transition": False,
                "next_step": self.get_next_step_suggestion(),
                "alert_type": "UNEXPECTED",
                "message": f"Observed unknown step: {observed_step_id}"
            }

        # Case 1: Re-observation of the current step
        if observed_step_id == self.current_step_id:
            self.last_alert_type = "OK"
            return {
                "current_step": self.current_step_id,
                "is_valid_transition": True,
                "next_step": self.get_next_step_suggestion(),
                "alert_type": "REPEATED",
                "message": f"Step {observed_step_id} ongoing / re-observed"
            }

        # Case 2: Valid transition to next step
        allowed_next = self.graph.get_allowed_next(self.current_step_id)
        if observed_step_id in allowed_next:
            self.completed_steps.append(self.current_step_id)
            self.current_step_id = observed_step_id
            self.last_alert_type = "OK"

            is_complete = "COMPLETE" in self.graph.get_allowed_next(self.current_step_id)
            alert = "COMPLETED" if is_complete else "OK"
            self.last_alert_type = alert

            return {
                "current_step": self.current_step_id,
                "is_valid_transition": True,
                "next_step": self.get_next_step_suggestion(),
                "alert_type": alert,
                "message": f"Valid transition to {observed_step_id}"
            }

        # Case 3: Out-of-order or skipped step logic
        all_step_ids = list(self.graph.steps.keys())
        current_idx = all_step_ids.index(self.current_step_id) if self.current_step_id in all_step_ids else -1
        target_idx = all_step_ids.index(observed_step_id) if observed_step_id in all_step_ids else -1

        if target_idx > current_idx + 1:
            alert = "SKIPPED"
        elif target_idx < current_idx and target_idx != -1:
            alert = "WRONG_ORDER"
        else:
            alert = "UNEXPECTED"

        self.last_alert_type = alert
        return {
            "current_step": self.current_step_id,
            "is_valid_transition": False,
            "next_step": self.get_next_step_suggestion(),
            "alert_type": alert,
            "message": f"Invalid step transition from {self.current_step_id} to {observed_step_id} ({alert})"
        }
