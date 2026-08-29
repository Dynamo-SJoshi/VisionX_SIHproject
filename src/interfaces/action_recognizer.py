from abc import ABC, abstractmethod
from typing import List
from src.schemas.track import Track
from src.schemas.action import ActionEvent


class ActionRecognizerInterface(ABC):
    """
    Abstract base class for recognizing human and tool interaction actions.
    """

    @abstractmethod
    def recognize(self, tracks: List[Track]) -> ActionEvent:
        """
        Analyze current tracks and temporal context to identify the performed action.
        
        Args:
            tracks: List of currently tracked entities.
            
        Returns:
            Standardized ActionEvent instance representing the classified action.
        """
        pass