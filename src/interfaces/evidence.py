"""
Evidence capture interface for BAS-HAR.

The evidence subsystem is responsible for capturing/referencing
visual or other supporting evidence for important events.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from src.schemas.action import ActionEvent
from src.schemas.decision import Decision
from src.schemas.evidence import EvidenceBundle


class EvidenceInterface(ABC):
    """
    Contract for evidence capture/storage implementations.
    """

    @abstractmethod
    def capture_for_action(
        self,
        action_event: ActionEvent,
        frame: Optional[Any] = None,
    ) -> EvidenceBundle:
        """
        Capture evidence supporting an ActionEvent.

        Args:
            action_event:
                Recognized action.

            frame:
                Optional current frame from the camera.

        Returns:
            EvidenceBundle:
                References to captured evidence.
        """
        raise NotImplementedError

    @abstractmethod
    def capture_for_decision(
        self,
        decision: Decision,
        frame: Optional[Any] = None,
    ) -> EvidenceBundle:
        """
        Capture evidence supporting a system decision.
        """
        raise NotImplementedError

    @abstractmethod
    def save_frame(
        self,
        frame: Any,
        evidence_id: str,
    ) -> Optional[str]:
        """
        Save a frame and return its storage path.

        Returns:
            Optional[str]:
                Path/reference to the stored frame.
        """
        raise NotImplementedError

    def name(self) -> str:
        """
        Human-readable evidence manager name.
        """
        return self.__class__.__name__