from abc import ABC, abstractmethod
from src.schemas.protocol import ValidationResult
from src.schemas.decision import Decision


class DecisionEngineInterface(ABC):
    """
    Abstract base class for evaluating protocol results into system decisions.
    """

    @abstractmethod
    def evaluate(self, validation_result: ValidationResult) -> Decision:
        """
        Evaluate protocol validation outcomes, confidence thresholds, and failure policies.
        
        Args:
            validation_result: Outcome produced by the protocol engine.
            
        Returns:
            Decision instance specifying system status, audio alerts, and recovery steps.
        """
        pass