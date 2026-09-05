# File: src/action/action_rules.py
from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from src.schemas.detection import Landmark
from src.schemas.track import Track
from src.schemas.action import ActionType, ActionStatus, ActionEvent
from src.spatial.spatial_reasoner import SpatialReasoner
from src.tracker.identity import TrackHistoryManager


class InteractionType(str, Enum):
    """Physical hand-object interaction classification states."""
    IDLE = "IDLE"
    APPROACH = "APPROACH"
    CONTACT = "CONTACT"
    HOLD_MOVE = "HOLD_MOVE"
    RELEASE = "RELEASE"


@dataclass
class HandObjectInteraction:
    """State record of an astronaut hand interacting with a specific object."""
    track_id: int
    class_name: str
    interaction_type: InteractionType
    distance_px: float
    rack_zone: str
    is_moving: bool
    confidence: float


class HandObjectInteractionDetector:
    """
    Evaluates physical proximity and kinematic movement between astronaut hands and tracked objects.
    Produces candidate ActionEvents for downstream temporal confirmation.
    """

    def __init__(
        self,
        contact_threshold: float = 55.0,
        approach_threshold: float = 130.0,
        spatial_reasoner: Optional[SpatialReasoner] = None
    ):
        self.contact_threshold = contact_threshold
        self.approach_threshold = approach_threshold
        self.spatial_reasoner = spatial_reasoner or SpatialReasoner()

    def evaluate_interactions(
        self,
        tracks: List[Track],
        hand_landmarks: List[Landmark],
        history: TrackHistoryManager
    ) -> List[HandObjectInteraction]:
        """
        Computes interaction states for all active experiment objects.

        Args:
            tracks: List of active object tracks.
            hand_landmarks: List of wrist and hand keypoint landmarks.
            history: TrackHistoryManager containing motion displacements.

        Returns:
            List of HandObjectInteraction records.
        """
        # Ensure rack zones are populated
        tracks = self.spatial_reasoner.update_object_zones(tracks)
        distances = self.spatial_reasoner.compute_hand_object_distances(tracks, hand_landmarks)

        interactions: List[HandObjectInteraction] = []

        for track in tracks:
            # Skip astronaut person box from being considered an experiment object
            if track.class_name == "astronaut":
                continue

            dist = distances.get(track.track_id, float("inf"))
            is_moving = history.is_moving(track.track_id, movement_threshold=12.0)

            # Classify interaction state
            if dist <= self.contact_threshold:
                if is_moving:
                    itype = InteractionType.HOLD_MOVE
                    conf = 0.92
                else:
                    itype = InteractionType.CONTACT
                    conf = 0.88
            elif dist <= self.approach_threshold:
                itype = InteractionType.APPROACH
                conf = 0.80
            else:
                itype = InteractionType.IDLE
                conf = 0.95

            interactions.append(HandObjectInteraction(
                track_id=track.track_id,
                class_name=track.class_name,
                interaction_type=itype,
                distance_px=dist,
                rack_zone=track.rack_zone or "FREE_SPACE",
                is_moving=is_moving,
                confidence=conf
            ))

        return interactions
