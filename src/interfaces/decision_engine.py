"""
Decision engine interface for BAS-HAR.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.schemas.protocol import ValidationResult
from src.schemas.decision import Decision


class DecisionEngineInterface(ABC):
    """
    Contract for converting protocol validation results into
    actionable runtime decisions.
    """

    @abstractmethod
    def evaluate(
        self,
        validation_result: ValidationResult,
    ) -> Decision:
        """
        Convert a protocol validation result into a system decision.

        Possible decisions include:
            PROCEED
            ALERT
            VERIFY
            RECOVER
            PAUSE
            STOP
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """
        Reset decision-related state.
        """
        raise NotImplementedError

    def name(self) -> str:
        """
        Human-readable decision engine name.
        """
        return self.__class__.__name__