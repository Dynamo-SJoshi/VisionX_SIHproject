from abc import ABC, abstractmethod
from src.schemas.action import ActionEvent
from src.schemas.protocol import ValidationResult
from src.schemas.decision import Decision


class LoggerInterface(ABC):
    """
    Abstract base class for system and experiment audit logging.
    """

    @abstractmethod
    def log_event(self, action: ActionEvent, validation: ValidationResult, decision: Decision) -> None:
        """
        Record a complete inference and validation cycle.
        
        Args:
            action: Recognized action event schema.
            validation: Protocol validation output schema.
            decision: System decision schema.
        """
        pass