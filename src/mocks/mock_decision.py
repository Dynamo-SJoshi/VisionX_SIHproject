from src.interfaces.decision_engine import DecisionEngineInterface
from src.schemas.protocol import ValidationResult, ProtocolStatus
from src.schemas.decision import Decision, DecisionStatus, DecisionReason

class MockDecisionEngine(DecisionEngineInterface):
    def evaluate(self, validation: ValidationResult) -> Decision:
        print("[DECISION] Evaluating result")
        
        if validation.status == ProtocolStatus.VALID:
            return Decision(
                decision_id="dec_mock_01",
                status=DecisionStatus.PROCEED,
                reason=DecisionReason.VALID_STEP,
                message="Protocol step completed successfully.",
                current_step_id=validation.current_step_id,
                next_step_id=validation.next_step_id,
                confidence=validation.confidence,
                requires_attention=False,
                protocol_advances=True
            )
            
        elif validation.status == ProtocolStatus.INVALID:
            return Decision(
                decision_id="dec_mock_02",
                status=DecisionStatus.RECOVER,
                reason=DecisionReason.WRONG_SEQUENCE,
                message=validation.message,
                current_step_id=validation.current_step_id,
                recovery_step_id=validation.recovery_step_id,
                confidence=validation.confidence,
                requires_attention=True,
                protocol_advances=False,
                should_speak=True,
                voice_message="Warning: Incorrect action detected."
            )
            
        return Decision(
            decision_id="dec_mock_03",
            status=DecisionStatus.VERIFY,
            reason=DecisionReason.LOW_CONFIDENCE,
            message="Unable to confidently validate action.",
            current_step_id=validation.current_step_id,
            confidence=validation.confidence,
            requires_attention=True,
            protocol_advances=False
        )