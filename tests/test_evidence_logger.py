"""
Unit tests for BAS-HAR EvidenceManager and SQLiteLogger.
"""

from pathlib import Path
import time
from PIL import Image
import pytest

from src.evidence.evidence_manager import EvidenceManager
from src.logger.sqlite_logger import SQLiteLogger
from src.schemas.action import ActionEvent, ActionType, EventStatus, ObjectInteraction
from src.schemas.decision import Decision, DecisionReason, DecisionStatus
from src.schemas.evidence import EvidenceType
from src.schemas.protocol import ProtocolStatus, ValidationResult


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def sqlite_logger(tmp_dir: Path) -> SQLiteLogger:
    db_file = tmp_dir / "test_events.db"
    return SQLiteLogger(db_path=db_file)


@pytest.fixture
def evidence_mgr(tmp_dir: Path) -> EvidenceManager:
    snap_dir = tmp_dir / "snapshots"
    return EvidenceManager(storage_dir=snap_dir)


class TestSQLiteLogger:

    def test_session_lifecycle_and_logging(self, sqlite_logger: SQLiteLogger, tmp_dir: Path):
        """Verify session creation, event insertion, querying, and CSV export."""
        session_id = "EXP_SQLITE_TEST_01"
        sqlite_logger.start_session(session_id, "sample_transfer_v1", time.time())

        # Create dummy action, validation, decision
        target_obj = ObjectInteraction(
            object_id="tube_A", object_label="sample_tube", role="target", confidence=0.95
        )
        action = ActionEvent(
            event_id="evt_test_sql",
            session_id=session_id,
            sequence_number=1,
            actor_id="astronaut_01",
            action=ActionType.IDENTIFY,
            confidence=0.95,
            status=EventStatus.VALIDATED,
            target_object=target_obj,
            interaction_zone="WORKBENCH",
        )
        validation = ValidationResult(
            status=ProtocolStatus.VALID,
            current_step_id="S1",
            expected_action=ActionType.IDENTIFY,
            observed_action=ActionType.IDENTIFY,
            confidence=0.95,
            message="Step S1 verified.",
            next_step_id="S2",
            protocol_can_advance=True,
        )
        decision = Decision(
            decision_id="dec_test_sql",
            status=DecisionStatus.PROCEED,
            reason=DecisionReason.VALID_STEP,
            message="Proceed to S2.",
            current_step_id="S1",
            next_step_id="S2",
            confidence=0.95,
        )

        record_id = sqlite_logger.log_pipeline_event(
            session_id=session_id,
            action=action,
            validation=validation,
            decision=decision,
            evidence_id="ev_001",
            snapshot_path="/path/to/snap.jpg",
        )
        assert record_id > 0

        # Query events
        events = sqlite_logger.get_session_events(session_id)
        assert len(events) == 1
        assert events[0]["event_id"] == "evt_test_sql"
        assert events[0]["action"] == "identify"
        assert events[0]["validation_status"] == "valid"
        assert events[0]["decision_status"] == "proceed"
        assert events[0]["evidence_id"] == "ev_001"

        # Export CSV
        csv_path = tmp_dir / "export_test.csv"
        sqlite_logger.export_session_csv(session_id, csv_path)
        assert csv_path.exists()
        with open(csv_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "evt_test_sql" in content
            assert "sample_transfer_v1" in content


class TestEvidenceManager:

    def test_save_frame_and_capture_action(self, evidence_mgr: EvidenceManager):
        """Verify saving a PIL image frame and building an Action evidence bundle."""
        # Create a test PIL image
        img = Image.new("RGB", (100, 100), color="blue")

        action = ActionEvent(
            event_id="evt_ev_test",
            session_id="EXP_EV_01",
            sequence_number=1,
            actor_id="astronaut_01",
            action=ActionType.PICK,
            confidence=0.92,
            status=EventStatus.VALIDATED,
            interaction_zone="WORKBENCH",
        )

        bundle = evidence_mgr.capture_for_action(action, frame=img)
        assert bundle.evidence_id.startswith("ev_act_")
        assert bundle.action_event_id == "evt_ev_test"
        assert len(bundle.items) == 1

        item = bundle.items[0]
        assert item.evidence_type == EvidenceType.VISUAL
        assert item.snapshot_path is not None
        assert Path(item.snapshot_path).exists()

    def test_capture_decision_violation(self, evidence_mgr: EvidenceManager):
        """Verify generating evidence for a procedure violation decision."""
        decision = Decision(
            decision_id="dec_ev_violation",
            status=DecisionStatus.ALERT,
            reason=DecisionReason.WRONG_SEQUENCE,
            message="Procedure violation: Skipped step S1.",
            current_step_id="S1",
            confidence=0.91,
            requires_attention=True,
        )

        img = Image.new("RGB", (100, 100), color="red")
        bundle = evidence_mgr.capture_for_decision(decision, frame=img)

        assert bundle.evidence_id.startswith("ev_dec_")
        assert bundle.decision_id == "dec_ev_violation"
        assert len(bundle.items) == 1
        assert "Procedure violation" in bundle.items[0].description
        assert Path(bundle.items[0].snapshot_path).exists()
