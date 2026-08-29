"""
Mock protocol engine for BAS-HAR integration testing.
"""

from __future__ import annotations

from src.interfaces.protocol_engine import ProtocolEngineInterface
from src.schemas.action import ActionEvent, ActionType
from src.schemas.protocol import (
    ExperimentProtocol,
    ProtocolStatus,
    ValidationResult,
)


class MockProtocolEngine(ProtocolEngineInterface):
    """
    Minimal deterministic protocol engine.

    Used to verify that the M1 pipeline correctly connects
    ActionEvent → ValidationResult.
    """

    def __init__(self) -> None:

        self.expected_action = ActionType.TRANSFER

        self.current_step = "S4"

        self.next_step = "S5"

        self.loaded_protocol = None

    def validate(
        self,
        action_event: ActionEvent,
    ) -> ValidationResult:

        print("[PROTOCOL] Validating action")

        # ------------------------------------------------------------
        # UNCERTAIN ACTION
        # ------------------------------------------------------------

        if action_event.status.value == "uncertain":

            return ValidationResult(
                status=ProtocolStatus.UNCERTAIN,

                current_step_id=self.current_step,

                expected_action=self.expected_action,

                observed_action=action_event.action,

                expected_object_id="tube_A",

                observed_object_id=(
                    action_event.target_object.object_id
                    if action_event.target_object
                    else None
                ),

                confidence=action_event.confidence,

                message=(
                    "Action confidence is insufficient for "
                    "safe protocol validation."
                ),

                next_step_id=self.next_step,

                protocol_can_advance=False,

                recovery_step_id=self.current_step,

                violation_code="LOW_CONFIDENCE",
            )

        # ------------------------------------------------------------
        # VALID ACTION
        # ------------------------------------------------------------

        if action_event.action == self.expected_action:

            return ValidationResult(
                status=ProtocolStatus.VALID,

                current_step_id=self.current_step,

                expected_action=self.expected_action,

                observed_action=action_event.action,

                expected_object_id="tube_A",

                observed_object_id=(
                    action_event.target_object.object_id
                    if action_event.target_object
                    else None
                ),

                confidence=action_event.confidence,

                message=(
                    "Action matches expected protocol step."
                ),

                next_step_id=self.next_step,

                protocol_can_advance=True,

                recovery_step_id=None,

                violation_code=None,
            )

        # ------------------------------------------------------------
        # INVALID ACTION
        # ------------------------------------------------------------

        return ValidationResult(
            status=ProtocolStatus.INVALID,

            current_step_id=self.current_step,

            expected_action=self.expected_action,

            observed_action=action_event.action,

            expected_object_id="tube_A",

            observed_object_id=(
                action_event.target_object.object_id
                if action_event.target_object
                else None
            ),

            confidence=action_event.confidence,

            message=(
                f"Unexpected action detected. "
                f"Expected '{self.expected_action.value}', "
                f"observed '{action_event.action.value}'."
            ),

            next_step_id=None,

            protocol_can_advance=False,

            recovery_step_id=self.current_step,

            violation_code="WRONG_ACTION",
        )

    def load_protocol(
        self,
        protocol: ExperimentProtocol,
    ) -> None:
        """
        Load an experiment protocol.

        For the mock implementation we use the protocol's initial state.
        """

        self.loaded_protocol = protocol

        self.current_step = protocol.initial_step_id

        self.next_step = None

        if protocol.steps:

            first_step = protocol.steps[0]

            self.expected_action = first_step.action

            if first_step.allowed_next:
                self.next_step = first_step.allowed_next[0]

    def reset(self) -> None:
        """
        Reset the mock protocol to its initial demonstration state.
        """

        self.current_step = "S1"

        self.next_step = "S2"

        self.expected_action = ActionType.IDENTIFY

    def get_current_step_id(self) -> str:
        """
        Return current protocol step ID.
        """

        return self.current_step

    def get_expected_action(self) -> str:
        """
        Return expected action for current step.
        """

        return self.expected_action.value