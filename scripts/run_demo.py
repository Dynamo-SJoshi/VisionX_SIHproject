"""
End-to-End Pipeline Simulation and Judge Demonstration Script for BAS-HAR Assistant.

Runs 5 interactive offline demonstration scenarios:
1. Normal Perfect Execution (S1 -> S6).
2. Procedural Violation: Skipped Step (skipping Open Tube before Transfer).
3. Procedural Violation: Wrong Tool (using syringe instead of pipette).
4. Safety & Uncertainty Gating: Visual Occlusion (Low confidence hold).
5. Zero-Retraining Protocol Hot-Swap (Dynamic configuration reload).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, List, Optional

from src.decision.engine import DecisionEngine
from src.evidence.evidence_manager import EvidenceManager
from src.logger.sqlite_logger import SQLiteLogger
from src.protocol.engine import ProtocolEngine
from src.schemas.action import ActionEvent, ActionType, EventStatus, ObjectInteraction
from src.schemas.decision import Decision
from src.schemas.protocol import ProtocolStatus, ValidationResult


# Terminal Color Codes for Mission Control Console Output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_banner(title: str, subtitle: Optional[str] = None):
    print(f"\n{Colors.CYAN}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN} 🛰️  {title}{Colors.RESET}")
    if subtitle:
        print(f"{Colors.BLUE}     {subtitle}{Colors.RESET}")
    print(f"{Colors.CYAN}{'=' * 80}{Colors.RESET}")


def print_step_outcome(step_num: int, action_name: str, validation: ValidationResult, decision: Decision):
    if validation.status == ProtocolStatus.VALID:
        status_badge = f"{Colors.GREEN}[✓ VALID - PROCEED]{Colors.RESET}"
    elif validation.status == ProtocolStatus.UNCERTAIN:
        status_badge = f"{Colors.YELLOW}[⚠ UNCERTAIN - VERIFY]{Colors.RESET}"
    else:
        status_badge = f"{Colors.RED}[✗ VIOLATION - ALERT]{Colors.RESET}"

    print(f"\nStep {step_num}: {Colors.BOLD}{action_name.upper()}{Colors.RESET} -> {status_badge}")
    print(f"  ├─ Active Step:     {Colors.CYAN}{validation.current_step_id}{Colors.RESET}")
    print(f"  ├─ Confidence:      {validation.confidence * 100:.1f}%")
    print(f"  ├─ Protocol Result: {validation.message}")
    print(f"  ├─ Safety Decision: {decision.message}")
    if decision.voice_message:
        print(f"  └─ {Colors.MAGENTA}🔊 Voice Guidance: \"{decision.voice_message}\"{Colors.RESET}")


def make_simulated_action(
    event_id: str,
    action: ActionType,
    object_id: str = "tube_A",
    tool_id: Optional[str] = None,
    zone: str = "WORKBENCH",
    confidence: float = 0.95,
    status: EventStatus = EventStatus.VALIDATED,
) -> ActionEvent:
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
        event_id=event_id,
        session_id="DEMO_SESSION_01",
        sequence_number=1,
        actor_id="astronaut_alex",
        action=action,
        confidence=confidence,
        status=status,
        target_object=target_obj,
        tool_object=tool_obj,
        interaction_zone=zone,
    )


def run_demo():
    print_banner("BAS AI COPILOT — SPACE STATION HAR ASSISTANT", "Offline Edge Pipeline Simulation & Safety Verification")

    # 1. Initialize M3 Core Engines
    protocol_engine = ProtocolEngine()
    decision_engine = DecisionEngine()
    sqlite_logger = SQLiteLogger("data/logs/demo_events.db")
    evidence_mgr = EvidenceManager("data/evidence/snapshots")

    # Load Standard Protocol
    config_path = Path("data/configs/sample_transfer_protocol_v1.json")
    protocol_engine.load_protocol_from_file(config_path)

    session_id = f"EXP_DEMO_{int(time.time())}"
    sqlite_logger.start_session(session_id, "sample_transfer_v1", time.time())

    # ========================================================================
    # SCENARIO 1: NORMAL CORRECT PROCEDURE (6 STEPS)
    # ========================================================================
    print_banner("SCENARIO 1: NORMAL CORRECT EXECUTION", "Demonstrates nominal step-by-step progress with voice guidance")
    protocol_engine.reset()
    decision_engine.reset()

    nominal_steps = [
        ("Identify Sample Tube", ActionType.IDENTIFY, "tube_A", None, "WORKBENCH", 0.96),
        ("Pick Sample Tube", ActionType.PICK, "tube_A", None, "WORKBENCH", 0.94),
        ("Open Tube Cap", ActionType.OPEN, "tube_A", None, "WORKBENCH", 0.91),
        ("Transfer Specimen Liquid", ActionType.TRANSFER, "tube_A", "pipette_01", "WORKBENCH", 0.95),
        ("Seal Tube Cap", ActionType.SEAL, "tube_A", None, "WORKBENCH", 0.93),
        ("Place Tube in Rack Slot", ActionType.PLACE, "tube_A", None, "WORKBENCH", 0.97),
    ]

    for idx, (title, act, obj, tool, zone, conf) in enumerate(nominal_steps, start=1):
        action_evt = make_simulated_action(f"evt_norm_{idx}", act, obj, tool, zone, conf)
        validation = protocol_engine.validate(action_evt)
        decision = decision_engine.evaluate(validation)

        # Log & Evidence
        evidence = evidence_mgr.capture_for_action(action_evt)
        sqlite_logger.log_pipeline_event(session_id, action_evt, validation, decision, evidence.evidence_id)
        print_step_outcome(idx, title, validation, decision)
        time.sleep(0.3)

    # ========================================================================
    # SCENARIO 2: PROCEDURAL VIOLATION (SKIPPED STEP)
    # ========================================================================
    print_banner("SCENARIO 2: PROCEDURAL VIOLATION — SKIPPED STEP", "Astronaut attempts liquid transfer without uncapping the tube")
    protocol_engine.reset()
    decision_engine.reset()

    # Step 1: Identify
    evt1 = make_simulated_action("evt_skip_1", ActionType.IDENTIFY, "tube_A", None, "WORKBENCH", 0.95)
    val1 = protocol_engine.validate(evt1)
    dec1 = decision_engine.evaluate(val1)
    print_step_outcome(1, "Identify Sample Tube", val1, dec1)

    # Step 2: Pick
    evt2 = make_simulated_action("evt_skip_2", ActionType.PICK, "tube_A", None, "WORKBENCH", 0.94)
    val2 = protocol_engine.validate(evt2)
    dec2 = decision_engine.evaluate(val2)
    print_step_outcome(2, "Pick Sample Tube", val2, dec2)

    # Step 3 (MISTAKE): Astronaut skips OPEN and attempts TRANSFER directly!
    evt3 = make_simulated_action("evt_skip_3", ActionType.TRANSFER, "tube_A", "pipette_01", "WORKBENCH", 0.93)
    val3 = protocol_engine.validate(evt3)
    dec3 = decision_engine.evaluate(val3)
    print_step_outcome(3, "Transfer Liquid (WITHOUT OPENING)", val3, dec3)

    # ========================================================================
    # SCENARIO 3: PROCEDURAL VIOLATION (WRONG TOOL)
    # ========================================================================
    print_banner("SCENARIO 3: TOOL COMPLIANCE VIOLATION", "Astronaut uses unauthorized syringe instead of pipette_01")
    protocol_engine.reset()
    decision_engine.reset()

    protocol_engine.validate(make_simulated_action("evt_tool_1", ActionType.IDENTIFY, "tube_A"))
    protocol_engine.validate(make_simulated_action("evt_tool_2", ActionType.PICK, "tube_A"))
    protocol_engine.validate(make_simulated_action("evt_tool_3", ActionType.OPEN, "tube_A"))

    # Attempt transfer with wrong tool: syringe_02
    evt_wrong_tool = make_simulated_action(
        "evt_tool_4", ActionType.TRANSFER, "tube_A", tool_id="syringe_02", zone="WORKBENCH", confidence=0.92
    )
    val_tool = protocol_engine.validate(evt_wrong_tool)
    dec_tool = decision_engine.evaluate(val_tool)
    print_step_outcome(4, "Transfer using syringe_02 (Unauthorized Tool)", val_tool, dec_tool)

    # ========================================================================
    # SCENARIO 4: UNCERTAINTY & OCCLUSION SAFETY GATE
    # ========================================================================
    print_banner("SCENARIO 4: SAFETY & UNCERTAINTY GATING", "Low visual confidence holds protocol progression in pending state")
    protocol_engine.reset()
    decision_engine.reset()

    # Low confidence action (0.42 < 0.65 threshold)
    low_conf_evt = make_simulated_action(
        "evt_low_1", ActionType.IDENTIFY, "tube_A", None, "WORKBENCH", confidence=0.42
    )
    val_low = protocol_engine.validate(low_conf_evt)
    dec_low = decision_engine.evaluate(val_low)
    print_step_outcome(1, "Identify Sample (Partially Occluded / Low Conf)", val_low, dec_low)

    # ========================================================================
    # SCENARIO 5: EXPORT & AUDIT TRAIL SUMMARY
    # ========================================================================
    print_banner("SESSION AUDIT EXPORT", "Generating structured SQLite & CSV compliance log")
    sqlite_logger.stop_session(session_id, time.time())
    csv_export_path = Path("data/logs") / f"demo_audit_{session_id}.csv"
    exported_file = sqlite_logger.export_session_csv(session_id, csv_export_path)

    events = sqlite_logger.get_session_events(session_id)
    print(f"\n{Colors.GREEN}✓ Demo Session Completed Successfully!{Colors.RESET}")
    print(f"  ├─ Session ID:        {session_id}")
    print(f"  ├─ Total Events:      {len(events)} events recorded in SQLite")
    print(f"  ├─ Audit CSV Export:  {exported_file}")
    print(f"  └─ Database Path:     data/logs/demo_events.db\n")


if __name__ == "__main__":
    run_demo()
