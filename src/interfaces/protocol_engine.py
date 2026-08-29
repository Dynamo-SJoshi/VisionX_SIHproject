"""
Protocol engine interface for BAS-HAR.

The protocol engine determines whether an observed ActionEvent
is valid according to the currently loaded experiment protocol.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.schemas.action import ActionEvent
from src.schemas.protocol import (
    ExperimentProtocol,
    ValidationResult,
)


class ProtocolEngineInterface(ABC):
    """
    Contract for experiment protocol validation implementations.
    """

    @abstractmethod
    def validate(
        self,
        action_event: ActionEvent,
    ) -> ValidationResult:
        """
        Validate an observed action against the current protocol state.

        Args:
            action_event:
                Action recognized by the perception/action layer.

        Returns:
            ValidationResult:
                Result of protocol validation.
        """
        raise NotImplementedError

    @abstractmethod
    def load_protocol(
        self,
        protocol: ExperimentProtocol,
    ) -> None:
        """
        Load or replace the active experiment protocol.
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """
        Reset the current protocol execution state to its initial state.
        """
        raise NotImplementedError

    @abstractmethod
    def get_current_step_id(self) -> Optional[str]:
        """
        Return the ID of the currently active protocol step.
        """
        raise NotImplementedError

    @abstractmethod
    def get_expected_action(self) -> Optional[str]:
        """
        Return the expected action for the current protocol step.

        Returning None is allowed when no protocol is loaded.
        """
        raise NotImplementedError

    def name(self) -> str:
        """
        Human-readable protocol engine name.
        """
        return self.__class__.__name__