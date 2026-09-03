"""
Mock action recognizer for BAS-HAR integration testing.

This generates realistic ActionEvent objects that are compatible
with the advanced action schema.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from src.interfaces.action_recognizer import ActionRecognizerInterface
from src.schemas.action import (
    ActionEvent,
    ActionType,
    EventStatus,
    HandType,
    ObjectInteraction,
    RecognitionSource,
)
from src.schemas.spatial import SpatialState
from src.schemas.track import Track


class MockActionRecognizer(ActionRecognizerInterface):
    """
    Deterministic action recognizer.

    By default it generates a TRANSFER event.
    """

    def __init__(
        self,
        action: ActionType = ActionType.TRANSFER,
        confidence: float = 0.94,
    ) -> None:

        self.action = action
        self.confidence = confidence
        self._sequence_number = 0

    def recognize(
        self,
        tracks: List[Track],
        spatial_state: Optional[SpatialState] = None,
    ) -> Optional[ActionEvent]:

        print("[ACTION] Recognizing action")

        self._sequence_number += 1

        target_object = ObjectInteraction(
            object_id="tube_A",
            object_label="sample_tube",
            role="target",
            confidence=0.95,
        )

        event = ActionEvent(
            event_id=f"act_mock_{self._sequence_number:04d}",

            session_id="session_mock_001",

            sequence_number=self._sequence_number,

            timestamp=datetime.now(timezone.utc),

            actor_id="astronaut_01",

            hand=HandType.RIGHT,

            action=self.action,

            target_object=target_object,

            confidence=self.confidence,

            status=(
                EventStatus.UNCERTAIN
                if self.confidence < 0.60
                else EventStatus.VALIDATED
            ),

            recognition_source=RecognitionSource.MOCK,

            actor_confidence=0.98,

            object_confidence=0.95,

            interaction_confidence=self.confidence,

            temporal_confidence=0.90,

            spatial_confidence=(
                0.90 if spatial_state is not None else None
            ),

            interaction_zone="TRANSFER_ZONE",

            supporting_track_ids=[
                track.track_id
                for track in tracks
            ],

            supporting_detection_ids=[],

            reasoning_summary=(
                "Mock recognizer generated a deterministic action "
                "for integration testing."
            ),
        )

        return event

    def reset(self) -> None:
        """Reset action recognition state."""
        self._sequence_number = 0

    def set_action(
        self,
        action: ActionType,
    ) -> None:
        """
        Change the action produced by the mock recognizer.

        Useful for testing:
            PICK
            OPEN
            TRANSFER
            SEAL
            etc.
        """
        self.action = action

    def set_confidence(
        self,
        confidence: float,
    ) -> None:
        """
        Change the confidence produced by the mock recognizer.
        """

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "Confidence must be between 0 and 1."
            )

        self.confidence = confidence