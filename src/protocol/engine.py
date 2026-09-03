"""
Real Protocol Engine implementation for BAS-HAR.

This module validates observed ActionEvents against a directed experiment protocol
graph, tracks execution state, enforces safety/ordering rules, and outputs 3-state
ValidationResults (VALID, INVALID, UNCERTAIN).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.interfaces.protocol_engine import ProtocolEngineInterface
from src.schemas.action import ActionEvent, ActionType, EventStatus
from src.schemas.protocol import (
    ExperimentProtocol,
    ProtocolStatus,
    ProtocolStep,
    ValidationResult,
)


class ProtocolEngine(ProtocolEngineInterface):
    """
    State machine and graph validator for experiment protocols.

    Maintains:
    - Currently active protocol definition (ExperimentProtocol).
    - Current step pointer (current_step_id).
    - Completed step sequence history.
    - Safety confidence threshold for uncertainty gating.
    """

    def __init__(
        self,
        protocol: Optional[ExperimentProtocol] = None,
        confidence_threshold: float = 0.65,
    ) -> None:
        self._protocol: Optional[ExperimentProtocol] = None
        self._steps_by_id: Dict[str, ProtocolStep] = {}
        self._current_step_id: Optional[str] = None
        self._completed_step_ids: List[str] = []
        self._confidence_threshold = confidence_threshold
        self._validation_history: List[ValidationResult] = []

        if protocol is not None:
            self.load_protocol(protocol)

    # ========================================================================
    # PROTOCOL LIFECYCLE MANAGEMENT
    # ========================================================================

    def load_protocol(self, protocol: ExperimentProtocol) -> None:
        """
        Loads or hot-swaps an experiment protocol definition.
        Resets active state to the protocol's initial step.
        """
        self._protocol = protocol
        self._steps_by_id = {step.id: step for step in protocol.steps}
        self._current_step_id = protocol.initial_step_id
        self._completed_step_ids = []
        self._validation_history = []

    def load_protocol_from_file(self, config_path: str | Path) -> None:
        """
        Loads experiment protocol JSON file and initializes the engine.
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Protocol configuration file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        protocol = ExperimentProtocol.model_validate(data)
        self.load_protocol(protocol)

    def reset(self) -> None:
        """
        Resets execution state back to the initial step.
        """
        if self._protocol is not None:
            self._current_step_id = self._protocol.initial_step_id
        else:
            self._current_step_id = None
        self._completed_step_ids = []
        self._validation_history = []

    # ========================================================================
    # STATE ACCESSORS
    # ========================================================================

    def get_current_step_id(self) -> Optional[str]:
        """Returns the ID of the currently active protocol step."""
        return self._current_step_id

    def get_current_step(self) -> Optional[ProtocolStep]:
        """Returns the ProtocolStep model of the active step."""
        if not self._current_step_id:
            return None
        return self._steps_by_id.get(self._current_step_id)

    def get_expected_action(self) -> Optional[str]:
        """Returns string value of expected ActionType for current step."""
        current_step = self.get_current_step()
        if not current_step:
            return None
        return (
            current_step.action.value
            if hasattr(current_step.action, "value")
            else str(current_step.action)
        )

    def get_allowed_next_steps(self) -> List[str]:
        """Returns allowed next step IDs from the current state."""
        current_step = self.get_current_step()
        return current_step.allowed_next if current_step else []

    def get_completed_steps(self) -> List[str]:
        """Returns ordered list of completed step IDs."""
        return list(self._completed_step_ids)

    # ========================================================================
    # VALIDATION LOGIC
    # ========================================================================

    def validate(self, action_event: ActionEvent) -> ValidationResult:
        """
        Validates an observed ActionEvent against the active protocol graph.
        """
        # Case 0: No protocol loaded
        if self._protocol is None or self._current_step_id is None:
            result = ValidationResult(
                status=ProtocolStatus.UNCERTAIN,
                current_step_id="NONE",
                expected_action=ActionType.UNKNOWN,
                observed_action=action_event.action,
                confidence=action_event.confidence,
                message="No active experiment protocol is loaded.",
                protocol_can_advance=False,
                violation_code="NO_PROTOCOL",
            )
            self._validation_history.append(result)
            return result

        current_step = self.get_current_step()
        if not current_step:
            result = ValidationResult(
                status=ProtocolStatus.INVALID,
                current_step_id=self._current_step_id,
                expected_action=ActionType.UNKNOWN,
                observed_action=action_event.action,
                confidence=action_event.confidence,
                message=f"Current step ID '{self._current_step_id}' not found in protocol graph.",
                protocol_can_advance=False,
                violation_code="INVALID_STEP_ID",
            )
            self._validation_history.append(result)
            return result

        expected_action = (
            current_step.action
            if isinstance(current_step.action, ActionType)
            else ActionType(str(current_step.action))
        )
        observed_action = (
            action_event.action
            if isinstance(action_event.action, ActionType)
            else ActionType(str(action_event.action))
        )
        expected_act_str = expected_action.value
        observed_act_str = observed_action.value

        observed_object_id = (
            action_event.target_object.object_id if action_event.target_object else None
        )
        observed_tool_id = (
            action_event.tool_object.object_id if action_event.tool_object else None
        )

        # --------------------------------------------------------------------
        # 1. UNCERTAINTY & CONFIDENCE SAFETY GATE
        # --------------------------------------------------------------------
        is_uncertain_status = (
            action_event.status == EventStatus.UNCERTAIN
            or (hasattr(action_event.status, "value") and action_event.status.value == "uncertain")
        )
        is_low_confidence = action_event.confidence < self._confidence_threshold

        if is_uncertain_status or is_low_confidence:
            result = ValidationResult(
                status=ProtocolStatus.UNCERTAIN,
                current_step_id=self._current_step_id,
                expected_action=expected_action,
                observed_action=observed_action,
                expected_object_id=current_step.object_id,
                observed_object_id=observed_object_id,
                confidence=action_event.confidence,
                message=(
                    f"Action confidence ({action_event.confidence:.2f}) is below safety threshold "
                    f"({self._confidence_threshold:.2f}) or visual occlusion detected. Verification pending."
                ),
                next_step_id=self._get_primary_next_step(current_step),
                protocol_can_advance=False,
                recovery_step_id=self._current_step_id,
                violation_code="LOW_CONFIDENCE",
            )
            self._validation_history.append(result)
            return result

        # --------------------------------------------------------------------
        # 2. VALID MATCH: Action matches current step
        # --------------------------------------------------------------------
        if observed_action == expected_action:
            # Check Object requirement
            if current_step.object_id and observed_object_id != current_step.object_id:
                result = ValidationResult(
                    status=ProtocolStatus.INVALID,
                    current_step_id=self._current_step_id,
                    expected_action=expected_action,
                    observed_action=observed_action,
                    expected_object_id=current_step.object_id,
                    observed_object_id=observed_object_id,
                    confidence=action_event.confidence,
                    message=(
                        f"Object mismatch in step '{current_step.name}'. "
                        f"Expected object '{current_step.object_id}', observed '{observed_object_id}'."
                    ),
                    next_step_id=None,
                    protocol_can_advance=False,
                    recovery_step_id=self._current_step_id,
                    violation_code="WRONG_OBJECT",
                )
                self._validation_history.append(result)
                return result

            # Check Tool requirement
            if current_step.tool_id and observed_tool_id != current_step.tool_id:
                result = ValidationResult(
                    status=ProtocolStatus.INVALID,
                    current_step_id=self._current_step_id,
                    expected_action=expected_action,
                    observed_action=observed_action,
                    expected_object_id=current_step.object_id,
                    observed_object_id=observed_object_id,
                    confidence=action_event.confidence,
                    message=(
                        f"Tool mismatch in step '{current_step.name}'. "
                        f"Expected tool '{current_step.tool_id}', observed '{observed_tool_id}'."
                    ),
                    next_step_id=None,
                    protocol_can_advance=False,
                    recovery_step_id=self._current_step_id,
                    violation_code="WRONG_TOOL",
                )
                self._validation_history.append(result)
                return result

            # Check Allowed Zones
            if current_step.allowed_zones and action_event.interaction_zone:
                if action_event.interaction_zone not in current_step.allowed_zones:
                    result = ValidationResult(
                        status=ProtocolStatus.INVALID,
                        current_step_id=self._current_step_id,
                        expected_action=expected_action,
                        observed_action=observed_action,
                        expected_object_id=current_step.object_id,
                        observed_object_id=observed_object_id,
                        confidence=action_event.confidence,
                        message=(
                            f"Zone violation in step '{current_step.name}'. "
                            f"Action occurred in zone '{action_event.interaction_zone}', "
                            f"allowed zones: {current_step.allowed_zones}."
                        ),
                        next_step_id=None,
                        protocol_can_advance=False,
                        recovery_step_id=self._current_step_id,
                        violation_code="WRONG_ZONE",
                    )
                    self._validation_history.append(result)
                    return result

            # All checks passed: VALID STEP EXECUTION
            primary_next = self._get_primary_next_step(current_step)
            result = ValidationResult(
                status=ProtocolStatus.VALID,
                current_step_id=self._current_step_id,
                expected_action=expected_action,
                observed_action=observed_action,
                expected_object_id=current_step.object_id,
                observed_object_id=observed_object_id,
                confidence=action_event.confidence,
                message=f"Step '{current_step.name}' ({current_step.id}) verified successfully.",
                next_step_id=primary_next,
                protocol_can_advance=True,
                recovery_step_id=None,
                violation_code=None,
            )

            # Advance state
            self._completed_step_ids.append(self._current_step_id)
            if primary_next:
                self._current_step_id = primary_next

            self._validation_history.append(result)
            return result

        # --------------------------------------------------------------------
        # 3. PROCEDURAL VIOLATION CHECKS (Skipped, Repeated, Wrong Order)
        # --------------------------------------------------------------------
        
        # Check if observed action corresponds to a future step (Skipped step)
        future_step_match = self._find_matching_future_step(observed_action, observed_object_id)
        if future_step_match:
            future_id, future_name = future_step_match
            result = ValidationResult(
                status=ProtocolStatus.INVALID,
                current_step_id=self._current_step_id,
                expected_action=expected_action,
                observed_action=observed_action,
                expected_object_id=current_step.object_id,
                observed_object_id=observed_object_id,
                confidence=action_event.confidence,
                message=(
                    f"Procedure violation: Skipped step '{current_step.name}' ({current_step.id}). "
                    f"Astronaut attempted '{future_name}' ({future_id}) prematurely. "
                    f"Expected action: '{expected_act_str}'."
                ),
                next_step_id=None,
                protocol_can_advance=False,
                recovery_step_id=self._current_step_id,
                violation_code="SKIPPED_STEP",
            )
            self._validation_history.append(result)
            return result

        # Check if observed action corresponds to an already completed step (Repeated step)
        completed_step_match = self._find_matching_completed_step(observed_action, observed_object_id)
        if completed_step_match:
            comp_id, comp_name = completed_step_match
            result = ValidationResult(
                status=ProtocolStatus.INVALID,
                current_step_id=self._current_step_id,
                expected_action=expected_action,
                observed_action=observed_action,
                expected_object_id=current_step.object_id,
                observed_object_id=observed_object_id,
                confidence=action_event.confidence,
                message=(
                    f"Procedure violation: Repeated step '{comp_name}' ({comp_id}) which was already completed. "
                    f"Current required step is '{current_step.name}' ({current_step.id})."
                ),
                next_step_id=None,
                protocol_can_advance=False,
                recovery_step_id=self._current_step_id,
                violation_code="REPEATED_STEP",
            )
            self._validation_history.append(result)
            return result

        # Generic unexpected action
        result = ValidationResult(
            status=ProtocolStatus.INVALID,
            current_step_id=self._current_step_id,
            expected_action=expected_action,
            observed_action=observed_action,
            expected_object_id=current_step.object_id,
            observed_object_id=observed_object_id,
            confidence=action_event.confidence,
            message=(
                f"Unexpected action '{observed_act_str}' observed. "
                f"Expected '{expected_act_str}' for step '{current_step.name}' ({current_step.id})."
            ),
            next_step_id=None,
            protocol_can_advance=False,
            recovery_step_id=self._current_step_id,
            violation_code="UNEXPECTED_ACTION",
        )
        self._validation_history.append(result)
        return result

    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================

    def _get_primary_next_step(self, step: ProtocolStep) -> Optional[str]:
        """Returns the primary next step ID from step.allowed_next."""
        if step.allowed_next and len(step.allowed_next) > 0:
            return step.allowed_next[0]
        return None

    def _find_matching_future_step(
        self, action: ActionType, object_id: Optional[str]
    ) -> Optional[Tuple[str, str]]:
        """
        Traverses reachable future steps to detect if the observed action skipped ahead.
        """
        if not self._current_step_id:
            return None

        visited = set()
        queue = list(self.get_allowed_next_steps())

        while queue:
            step_id = queue.pop(0)
            if step_id in visited:
                continue
            visited.add(step_id)

            step = self._steps_by_id.get(step_id)
            if step:
                step_act = (
                    step.action
                    if isinstance(step.action, ActionType)
                    else ActionType(str(step.action))
                )
                if step_act == action:
                    if object_id is None or step.object_id is None or step.object_id == object_id:
                        return (step.id, step.name)
                queue.extend(step.allowed_next)

        return None

    def _find_matching_completed_step(
        self, action: ActionType, object_id: Optional[str]
    ) -> Optional[Tuple[str, str]]:
        """
        Checks if an action belongs to a previously completed step.
        """
        for step_id in self._completed_step_ids:
            step = self._steps_by_id.get(step_id)
            if step:
                step_act = (
                    step.action
                    if isinstance(step.action, ActionType)
                    else ActionType(str(step.action))
                )
                if step_act == action:
                    if object_id is None or step.object_id is None or step.object_id == object_id:
                        return (step.id, step.name)
        return None
