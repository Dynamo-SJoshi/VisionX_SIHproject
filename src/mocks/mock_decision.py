"""
Mock decision engine for BAS-HAR integration testing.
"""

from __future__ import annotations

from src.interfaces.decision_engine import DecisionEngineInterface
from src.schemas.decision import (
    Decision,
    DecisionReason,
    DecisionStatus,
)
from src.schemas.protocol import (
    ProtocolStatus,
    ValidationResult,
)


class MockDecisionEngine(DecisionEngineInterface):
    """
    Converts ValidationResult into Decision objects.
    """

    def __init__(self) -> None:
        self._decision_counter = 0

    def evaluate(
        self,
        validation_result: ValidationResult,
    ) -> Decision:

        print("[DECISION] Evaluating result")

        self._decision_counter += 1

        decision_id = (
            f"dec_mock_{self._decision_counter:04d}"
        )

        # ================================================================
        # VALID
        # ================================================================

        if validation_result.status == ProtocolStatus.VALID:

            return Decision(
                decision_id=decision_id,

                status=DecisionStatus.PROCEED,

                reason=DecisionReason.VALID_STEP,

                message=(
                    "Protocol step completed successfully."
                ),

                current_step_id=(
                    validation_result.current_step_id
                ),

                next_step_id=(
                    validation_result.next_step_id
                ),

                confidence=validation_result.confidence,

                requires_attention=False,

                protocol_advances=True,

                should_speak=True,

                voice_message=(
                    "Step completed. Proceed to the next step."
                ),
            )

        # ================================================================
        # INVALID
        # ================================================================

        if validation_result.status == ProtocolStatus.INVALID:

            reason = DecisionReason.WRONG_SEQUENCE

            if validation_result.violation_code == "WRONG_OBJECT":
                reason = DecisionReason.WRONG_OBJECT

            elif validation_result.violation_code == "WRONG_TOOL":
                reason = DecisionReason.WRONG_TOOL

            elif validation_result.violation_code == "WRONG_ZONE":
                reason = DecisionReason.WRONG_ZONE

            return Decision(
                decision_id=decision_id,

                status=DecisionStatus.RECOVER,

                reason=reason,

                message=validation_result.message,

                current_step_id=(
                    validation_result.current_step_id
                ),

                next_step_id=None,

                recovery_step_id=(
                    validation_result.recovery_step_id
                ),

                confidence=validation_result.confidence,

                requires_attention=True,

                protocol_advances=False,

                should_speak=True,

                voice_message=(
                    "Warning. Incorrect action detected. "
                    "Please return to the required step."
                ),
            )

        # ================================================================
        # UNCERTAIN
        # ================================================================

        return Decision(
            decision_id=decision_id,

            status=DecisionStatus.VERIFY,

            reason=DecisionReason.LOW_CONFIDENCE,

            message=(
                "Unable to confidently validate the action."
            ),

            current_step_id=(
                validation_result.current_step_id
            ),

            next_step_id=None,

            recovery_step_id=None,

            confidence=validation_result.confidence,

            requires_attention=True,

            protocol_advances=False,

            should_speak=True,

            voice_message=(
                "Unable to verify the action. "
                "Please hold position for recheck."
            ),
        )

    def reset(self) -> None:
        """
        Reset decision counter.
        """
        self._decision_counter = 0