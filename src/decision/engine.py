"""
Real Decision Engine implementation for BAS-HAR.

Converts protocol ValidationResult objects into actionable system Decisions
for the Mission Control UI, Offline TTS Voice Guidance, and SQLite Audit Logging.
"""

from __future__ import annotations

from typing import List, Optional
import uuid

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


class DecisionEngine(DecisionEngineInterface):
    """
    Transforms protocol validation outcomes into 3-state system responses:
    1. VALID -> PROCEED (Advance protocol, generate next-step guidance & voice)
    2. INVALID -> ALERT (Freeze progression, generate explainable alert & voice warning)
    3. UNCERTAIN -> VERIFY (Pause progression, request operator confirmation or camera adjustment)
    """

    def __init__(self) -> None:
        self._decision_count: int = 0
        self._history: List[Decision] = []

    def reset(self) -> None:
        """Resets decision history and counter."""
        self._decision_count = 0
        self._history = []

    def evaluate(self, validation_result: ValidationResult) -> Decision:
        """
        Evaluates a protocol ValidationResult and returns a deterministic Decision.
        """
        self._decision_count += 1
        decision_id = f"dec_{self._decision_count:05d}_{uuid.uuid4().hex[:6]}"

        # ====================================================================
        # 1. VALID STEP OUTCOME (GREEN GATE)
        # ====================================================================
        if validation_result.status == ProtocolStatus.VALID:
            next_step_str = (
                f" Proceed to {validation_result.next_step_id}."
                if validation_result.next_step_id
                else " Experiment complete."
            )
            decision = Decision(
                decision_id=decision_id,
                status=DecisionStatus.PROCEED,
                reason=DecisionReason.VALID_STEP,
                message=validation_result.message,
                current_step_id=validation_result.current_step_id,
                next_step_id=validation_result.next_step_id,
                recovery_step_id=None,
                confidence=validation_result.confidence,
                requires_attention=False,
                protocol_advances=True,
                should_speak=True,
                voice_message=f"Step confirmed.{next_step_str}",
            )
            self._history.append(decision)
            return decision

        # ====================================================================
        # 2. UNCERTAIN / LOW CONFIDENCE OUTCOME (AMBER GATE)
        # ====================================================================
        if validation_result.status == ProtocolStatus.UNCERTAIN:
            reason = (
                DecisionReason.LOW_CONFIDENCE
                if validation_result.violation_code == "LOW_CONFIDENCE"
                else DecisionReason.MISSING_EVIDENCE
            )
            decision = Decision(
                decision_id=decision_id,
                status=DecisionStatus.VERIFY,
                reason=reason,
                message=validation_result.message,
                current_step_id=validation_result.current_step_id,
                next_step_id=validation_result.next_step_id,
                recovery_step_id=validation_result.recovery_step_id or validation_result.current_step_id,
                confidence=validation_result.confidence,
                requires_attention=True,
                protocol_advances=False,
                should_speak=False,
                voice_message="Verification pending. Please ensure clear camera view.",
            )
            self._history.append(decision)
            return decision

        # ====================================================================
        # 3. INVALID / PROCEDURE VIOLATION OUTCOME (RED GATE)
        # ====================================================================
        reason = self._map_violation_code_to_reason(validation_result.violation_code)
        expected_act = (
            validation_result.expected_action.value
            if hasattr(validation_result.expected_action, "value")
            else str(validation_result.expected_action)
        )
        voice_warning = f"Procedure warning. Required step is: {expected_act}."

        decision = Decision(
            decision_id=decision_id,
            status=DecisionStatus.ALERT,
            reason=reason,
            message=validation_result.message,
            current_step_id=validation_result.current_step_id,
            next_step_id=None,
            recovery_step_id=validation_result.recovery_step_id or validation_result.current_step_id,
            confidence=validation_result.confidence,
            requires_attention=True,
            protocol_advances=False,
            should_speak=True,
            voice_message=voice_warning,
        )
        self._history.append(decision)
        return decision

    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================

    def _map_violation_code_to_reason(self, violation_code: Optional[str]) -> DecisionReason:
        """Maps protocol violation string codes to DecisionReason enum."""
        mapping = {
            "SKIPPED_STEP": DecisionReason.WRONG_SEQUENCE,
            "REPEATED_STEP": DecisionReason.WRONG_SEQUENCE,
            "WRONG_ORDER": DecisionReason.WRONG_SEQUENCE,
            "WRONG_OBJECT": DecisionReason.WRONG_OBJECT,
            "WRONG_TOOL": DecisionReason.WRONG_TOOL,
            "WRONG_ZONE": DecisionReason.WRONG_ZONE,
            "TIMEOUT": DecisionReason.TIMEOUT,
            "LOW_CONFIDENCE": DecisionReason.LOW_CONFIDENCE,
        }
        if violation_code and violation_code in mapping:
            return mapping[violation_code]
        return DecisionReason.WRONG_SEQUENCE
