from abc import ABC, abstractmethod
from src.schemas.action import ActionEvent
from src.schemas.protocol import ValidationResult


class ProtocolEngineInterface(ABC):
    """
    Abstract base class for protocol state machines and graph validators.
    """

    @abstractmethod
    def validate(self, action_event: ActionEvent) -> ValidationResult:
        """
        Validate an observed action event against the active protocol state.
        
        Args:
            action_event: The ActionEvent emitted by the action recognizer.
            
        Returns:
            ValidationResult indicating validity, transitions, and next expected steps.
        """
        pass

    @abstractmethod
    def get_expected_action(self) -> str:
        """Return the action type string expected at the current step."""
        pass

    @abstractmethod
    def get_current_state(self) -> str:
        """Return the current step identifier or state label."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset the protocol state machine back to its initial step."""
        pass