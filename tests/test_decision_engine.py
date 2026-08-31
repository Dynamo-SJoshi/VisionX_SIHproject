"""
Unit tests for BAS-HAR DecisionEngine.

Verifies:
1. 3-state system responses: PROCEED (Valid), ALERT (Violation), VERIFY (Uncertain).
2. Voice guidance payload generation.
3. Attention requirement and protocol advance flags.
"""

import pytest

from src.decision.engine import DecisionEngine
from src.schemas.action import ActionType
from src.schemas.decision import DecisionReason, DecisionStatus
from src.schemas.protocol import ProtocolStatus, ValidationResult


@pytest.fixture
def decision_engine() -> DecisionEngine:
    return DecisionEngine()


class TestDecisionEngine:

    def test_valid_validation_yields_proceed(self, decision_engine: DecisionEngine):
        """Verify VALID protocol outcome creates PROCEED decision with voice guidance."""
        val = ValidationResult(
            status=ProtocolStatus.VALID,
            current_step_id="S1",
            expected_action=ActionType.IDENTIFY,
            observed_action=ActionType.IDENTIFY,
            expected_object_id="tube_A",
            observed_object_id="tube_A",
            confidence=0.96,
            message="Step 'Identify Sample' (S1) verified successfully.",
            next_step_id="S2",
            protocol_can_advance=True,
        )

        dec = decision_engine.evaluate(val)
        assert dec.status == DecisionStatus.PROCEED
        assert dec.reason == DecisionReason.VALID_STEP
        assert dec.protocol_advances is True
        assert dec.requires_attention is False
        assert dec.should_speak is True
        assert "Step confirmed. Proceed to S2." in dec.voice_message

    def test_uncertain_validation_yields_verify(self, decision_engine: DecisionEngine):
        """Verify UNCERTAIN protocol outcome creates VERIFY decision and pauses progression."""
        val = ValidationResult(
            status=ProtocolStatus.UNCERTAIN,
            current_step_id="S2",
            expected_action=ActionType.PICK,
            observed_action=ActionType.PICK,
            confidence=0.45,
            message="Action confidence below safety threshold.",
            next_step_id="S3",
            protocol_can_advance=False,
            recovery_step_id="S2",
            violation_code="LOW_CONFIDENCE",
        )

        dec = decision_engine.evaluate(val)
        assert dec.status == DecisionStatus.VERIFY
        assert dec.reason == DecisionReason.LOW_CONFIDENCE
        assert dec.protocol_advances is False
        assert dec.requires_attention is True
        assert dec.should_speak is False
        assert dec.recovery_step_id == "S2"

    def test_invalid_skipped_yields_alert(self, decision_engine: DecisionEngine):
        """Verify SKIPPED step violation creates ALERT decision with voice warning."""
        val = ValidationResult(
            status=ProtocolStatus.INVALID,
            current_step_id="S1",
            expected_action=ActionType.IDENTIFY,
            observed_action=ActionType.OPEN,
            confidence=0.92,
            message="Procedure violation: Skipped step 'Identify Sample'.",
            protocol_can_advance=False,
            recovery_step_id="S1",
            violation_code="SKIPPED_STEP",
        )

        dec = decision_engine.evaluate(val)
        assert dec.status == DecisionStatus.ALERT
        assert dec.reason == DecisionReason.WRONG_SEQUENCE
        assert dec.protocol_advances is False
        assert dec.requires_attention is True
        assert dec.should_speak is True
        assert "Procedure warning" in dec.voice_message

    def test_invalid_wrong_object_yields_wrong_object_alert(self, decision_engine: DecisionEngine):
        """Verify WRONG_OBJECT violation creates ALERT decision with WRONG_OBJECT reason."""
        val = ValidationResult(
            status=ProtocolStatus.INVALID,
            current_step_id="S2",
            expected_action=ActionType.PICK,
            observed_action=ActionType.PICK,
            confidence=0.90,
            message="Expected object 'tube_A', observed 'tube_B'.",
            protocol_can_advance=False,
            recovery_step_id="S2",
            violation_code="WRONG_OBJECT",
        )

        dec = decision_engine.evaluate(val)
        assert dec.status == DecisionStatus.ALERT
        assert dec.reason == DecisionReason.WRONG_OBJECT
        assert dec.protocol_advances is False
        assert dec.requires_attention is True
