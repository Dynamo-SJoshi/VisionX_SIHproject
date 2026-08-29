from src.interfaces.protocol_engine import ProtocolEngineInterface
from src.schemas.action import ActionEvent, ActionType
from src.schemas.protocol import ValidationResult, ProtocolStatus

class MockProtocolEngine(ProtocolEngineInterface):
    def __init__(self):
        self.expected_action = ActionType.TRANSFER
        self.current_step = "S4"

    def validate(self, action_event: ActionEvent) -> ValidationResult:
        print("[PROTOCOL] Validating action")
        
        if action_event.action == self.expected_action:
            return ValidationResult(
                status=ProtocolStatus.VALID,
                current_step_id=self.current_step,
                expected_action=self.expected_action,
                observed_action=action_event.action,
                confidence=action_event.confidence,
                message="Action matches expected protocol step.",
                next_step_id="S5",
                protocol_can_advance=True
            )
            
        return ValidationResult(
            status=ProtocolStatus.INVALID,
            current_step_id=self.current_step,
            expected_action=self.expected_action,
            observed_action=action_event.action,
            confidence=action_event.confidence,
            message="Unexpected action detected.",
            protocol_can_advance=False,
            recovery_step_id=self.current_step,
            violation_code="WRONG_ACTION"
        )

    def get_expected_action(self) -> str:
        return self.expected_action.value
        
    def get_current_state(self) -> str:
        return self.current_step
        
    def reset(self) -> None:
        self.current_step = "S1"
        self.expected_action = ActionType.IDENTIFY