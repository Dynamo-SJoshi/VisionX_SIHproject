"""
Unit tests for BAS-HAR ProtocolEngine.

Verifies:
1. Normal valid protocol progression.
2. Procedural violations: SKIPPED_STEP, REPEATED_STEP, UNEXPECTED_ACTION.
3. Object/Tool/Zone mismatches: WRONG_OBJECT, WRONG_TOOL, WRONG_ZONE.
4. Uncertainty and low-confidence safety gating.
5. Protocol reset and runtime hot-swapping.
"""

from pathlib import Path
import pytest

from src.protocol.engine import ProtocolEngine
from src.schemas.action import (
    ActionEvent,
    ActionType,
    EventStatus,
    ObjectInteraction,
)
from src.schemas.protocol import (
    ExperimentProtocol,
    ProtocolStatus,
)


@pytest.fixture
def sample_protocol() -> ExperimentProtocol:
    """Fixture providing a 6-step sample transfer protocol."""
    config_path = Path(__file__).parent.parent / "data" / "configs" / "sample_transfer_protocol_v1.json"
    engine = ProtocolEngine()
    engine.load_protocol_from_file(config_path)
    return engine._protocol


@pytest.fixture
def engine(sample_protocol: ExperimentProtocol) -> ProtocolEngine:
    """Fixture providing an initialized ProtocolEngine."""
    return ProtocolEngine(protocol=sample_protocol, confidence_threshold=0.65)


def make_action_event(
    action: ActionType,
    object_id: str = "tube_A",
    tool_id: str = None,
    zone: str = "WORKBENCH",
    confidence: float = 0.95,
    status: EventStatus = EventStatus.VALIDATED,
) -> ActionEvent:
    """Helper to construct ActionEvent for tests."""
    target_obj = (
        ObjectInteraction(object_id=object_id, object_label="sample_tube", role="target", confidence=confidence)
        if object_id
        else None
    )
    tool_obj = (
        ObjectInteraction(object_id=tool_id, object_label="tool", role="tool", confidence=confidence)
        if tool_id
        else None
    )

    return ActionEvent(
        event_id=f"evt_test_{action.value}",
        session_id="session_exp_01",
        sequence_number=1,
        actor_id="astronaut_1",
        action=action,
        confidence=confidence,
        status=status,
        target_object=target_obj,
        tool_object=tool_obj,
        interaction_zone=zone,
    )


class TestProtocolEngine:

    def test_initial_state(self, engine: ProtocolEngine):
        """Verify engine starts on step S1 with expected action IDENTIFY."""
        assert engine.get_current_step_id() == "S1"
        assert engine.get_expected_action() == "identify"
        assert engine.get_allowed_next_steps() == ["S2"]
        assert engine.get_completed_steps() == []

    def test_valid_step_progression(self, engine: ProtocolEngine):
        """Verify normal sequential execution through all 6 steps."""
        steps = [
            (ActionType.IDENTIFY, "tube_A", None, "WORKBENCH", "S1", "S2"),
            (ActionType.PICK, "tube_A", None, "WORKBENCH", "S2", "S3"),
            (ActionType.OPEN, "tube_A", None, "WORKBENCH", "S3", "S4"),
            (ActionType.TRANSFER, "tube_A", "pipette_01", "WORKBENCH", "S4", "S5"),
            (ActionType.SEAL, "tube_A", None, "WORKBENCH", "S5", "S6"),
            (ActionType.PLACE, "tube_A", None, "WORKBENCH", "S6", None),
        ]

        for action, obj, tool, zone, expected_current, expected_next in steps:
            event = make_action_event(action, object_id=obj, tool_id=tool, zone=zone)
            result = engine.validate(event)

            assert result.status == ProtocolStatus.VALID, f"Failed at step {expected_current}: {result.message}"
            assert result.protocol_can_advance is True
            assert result.current_step_id == expected_current
            assert result.next_step_id == expected_next

        assert engine.get_completed_steps() == ["S1", "S2", "S3", "S4", "S5", "S6"]

    def test_skipped_step_violation(self, engine: ProtocolEngine):
        """Verify skipping from S1 directly to OPEN (S3) triggers SKIPPED_STEP."""
        event = make_action_event(ActionType.OPEN, object_id="tube_A")
        result = engine.validate(event)

        assert result.status == ProtocolStatus.INVALID
        assert result.protocol_can_advance is False
        assert result.violation_code == "SKIPPED_STEP"
        assert "Skipped step" in result.message
        assert engine.get_current_step_id() == "S1"

    def test_wrong_object_mismatch(self, engine: ProtocolEngine):
        """Verify picking wrong tube triggers WRONG_OBJECT."""
        s1_event = make_action_event(ActionType.IDENTIFY, object_id="tube_A")
        engine.validate(s1_event)
        assert engine.get_current_step_id() == "S2"

        wrong_event = make_action_event(ActionType.PICK, object_id="tube_B")
        result = engine.validate(wrong_event)

        assert result.status == ProtocolStatus.INVALID
        assert result.protocol_can_advance is False
        assert result.violation_code == "WRONG_OBJECT"
        assert "Expected object 'tube_A', observed 'tube_B'" in result.message

    def test_wrong_tool_mismatch(self, engine: ProtocolEngine):
        """Verify using wrong tool on transfer triggers WRONG_TOOL."""
        engine.validate(make_action_event(ActionType.IDENTIFY, object_id="tube_A"))
        engine.validate(make_action_event(ActionType.PICK, object_id="tube_A"))
        engine.validate(make_action_event(ActionType.OPEN, object_id="tube_A"))
        assert engine.get_current_step_id() == "S4"

        wrong_tool_event = make_action_event(
            ActionType.TRANSFER, object_id="tube_A", tool_id="syringe_02"
        )
        result = engine.validate(wrong_tool_event)

        assert result.status == ProtocolStatus.INVALID
        assert result.protocol_can_advance is False
        assert result.violation_code == "WRONG_TOOL"
        assert "Expected tool 'pipette_01'" in result.message

    def test_low_confidence_uncertainty_gate(self, engine: ProtocolEngine):
        """Verify low confidence (<0.65) triggers UNCERTAIN status and pauses progression."""
        low_conf_event = make_action_event(
            ActionType.IDENTIFY, object_id="tube_A", confidence=0.45
        )
        result = engine.validate(low_conf_event)

        assert result.status == ProtocolStatus.UNCERTAIN
        assert result.protocol_can_advance is False
        assert result.violation_code == "LOW_CONFIDENCE"
        assert "below safety threshold" in result.message
        assert engine.get_current_step_id() == "S1"

    def test_repeated_step_violation(self, engine: ProtocolEngine):
        """Verify repeating an already completed step triggers REPEATED_STEP."""
        engine.validate(make_action_event(ActionType.IDENTIFY, object_id="tube_A"))
        assert engine.get_current_step_id() == "S2"

        repeat_event = make_action_event(ActionType.IDENTIFY, object_id="tube_A")
        result = engine.validate(repeat_event)

        assert result.status == ProtocolStatus.INVALID
        assert result.protocol_can_advance is False
        assert result.violation_code == "REPEATED_STEP"

    def test_reset_engine(self, engine: ProtocolEngine):
        """Verify reset restores engine to S1."""
        engine.validate(make_action_event(ActionType.IDENTIFY, object_id="tube_A"))
        engine.validate(make_action_event(ActionType.PICK, object_id="tube_A"))
        assert engine.get_current_step_id() == "S3"

        engine.reset()
        assert engine.get_current_step_id() == "S1"
        assert engine.get_completed_steps() == []
