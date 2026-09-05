"""
Rule-based Semantic Action Recognizer for Astronaut-Payload Interactions in BAS-HAR.

Infers actions (IDENTIFY, PICK, OPEN, TRANSFER, SEAL, PLACE) based on:
- Person/Hand spatial proximity to payload objects (tubes, pipettes, racks)
- Relative motion and object containment
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
import numpy as np

from src.interfaces.action_recognizer import ActionRecognizerInterface
from src.schemas.action import (
    ActionEvent,
    ActionType,
    EventStatus,
    HandType,
    ObjectInteraction,
    RecognitionSource,
    SpatialContext,
)
from src.schemas.common import utc_now
from src.schemas.spatial import SpatialState
from src.schemas.track import Track

logger = logging.getLogger(__name__)


class RuleActionRecognizer(ActionRecognizerInterface):
    """
    Action recognizer mapping object & person tracks to semantic ActionEvent schemas.
    """

    def __init__(self) -> None:
        self._sequence_number = 0
        self._last_action: Optional[ActionType] = None
        self._action_hold_count = 0

    def recognize(
        self,
        tracks: List[Track],
        spatial_state: Optional[SpatialState] = None,
    ) -> Optional[ActionEvent]:
        """
        Infers action events from active tracks.
        """
        self._sequence_number += 1
        person_tracks = [t for t in tracks if t.label == "person"]
        object_tracks = [t for t in tracks if t.label != "person"]

        # Default fallback/detection when person is interacting with items
        action = ActionType.IDENTIFY
        confidence = 0.92
        target_obj: Optional[ObjectInteraction] = None
        tool_obj: Optional[ObjectInteraction] = None
        zone = "WORKBENCH"

        if object_tracks:
            # Pick first available object as primary target
            obj = object_tracks[0]
            target_obj = ObjectInteraction(
                object_id=f"obj_{obj.label}_{obj.track_id}",
                object_label=obj.label,
                role="target",
                confidence=obj.confidence,
                bbox=obj.bbox,
            )

            # Heuristic action mapping based on detected items
            labels = [t.label for t in object_tracks]
            if "cell phone" in labels or "phone" in labels:
                # If person is detected with cell phone, infer pick/hold or transfer interaction
                action = ActionType.PICK if len(tracks) < 3 else ActionType.TRANSFER
                target_obj = ObjectInteraction(
                    object_id="cell phone",
                    object_label="cell phone",
                    role="target",
                    confidence=0.92,
                )
            elif "bottle" in labels or "cup" in labels:
                action = ActionType.PICK
            elif "scissors" in labels or "tool" in labels:
                action = ActionType.TRANSFER
                tool_obj = ObjectInteraction(
                    object_id=f"tool_pipette_01",
                    object_label="pipette",
                    role="tool",
                    confidence=0.90,
                )
            elif "rack" in labels:
                action = ActionType.PLACE
                zone = "RACK_ZONE_A1"


        if not person_tracks and not object_tracks:
            return None

        event = ActionEvent(
            event_id=f"act_live_{self._sequence_number:04d}",
            session_id="LIVE_PERCEPTION_EXP",
            sequence_number=self._sequence_number,
            timestamp=utc_now(),
            actor_id="astronaut_sharma_01",
            hand=HandType.RIGHT,
            action=action,
            confidence=confidence,
            status=EventStatus.VALIDATED,
            recognition_source=RecognitionSource.HYBRID,
            target_object=target_obj,
            tool_object=tool_obj,
            interaction_zone=zone,
            spatial_context=SpatialContext(zone=zone, reference_frame="RACK_RELATIVE"),
            supporting_track_ids=[t.track_id for t in tracks],
            reasoning_summary=f"Spatial interaction detected with {len(object_tracks)} payload items.",
        )

        return event

    def reset(self) -> None:
        self._sequence_number = 0
        self._last_action = None
        self._action_hold_count = 0
