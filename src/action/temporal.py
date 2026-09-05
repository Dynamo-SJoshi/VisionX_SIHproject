# File: src/action/temporal.py
import time
import logging
from collections import deque
from typing import List, Dict, Optional, Tuple

from src.schemas.action import ActionType, ActionStatus, ActionEvent
from src.action.action_rules import HandObjectInteraction, InteractionType

logger = logging.getLogger(__name__)


class ObjectActionHistory:
    """Tracks sequential interaction states over time for a single object track."""

    def __init__(self, track_id: int, class_name: str, window_size: int = 25):
        self.track_id = track_id
        self.class_name = class_name
        self.interaction_history: deque = deque(maxlen=window_size)
        self.timestamps: deque = deque(maxlen=window_size)
        self.current_state: str = "IDLE_ON_RACK"
        self.last_action_time: float = 0.0
        self.last_emitted_action: Optional[ActionType] = None

    def append(self, interaction: HandObjectInteraction, timestamp: float) -> None:
        """Appends new interaction state record."""
        self.interaction_history.append(interaction)
        self.timestamps.append(timestamp)

    def count_recent_state(self, itype: InteractionType, window: int = 10) -> int:
        """Counts occurrences of an interaction type in recent window."""
        recent = list(self.interaction_history)[-window:]
        return sum(1 for i in recent if i.interaction_type == itype)


class TemporalActionBuffer:
    """
    Multi-frame temporal sliding window action recognizer.
    Validates physical action sequences across time and enforces debounced action event emissions.
    """

    def __init__(self, window_size: int = 30, action_cooldown_seconds: float = 2.0):
        self.window_size = window_size
        self.cooldown = action_cooldown_seconds
        # Map track_id -> ObjectActionHistory
        self.object_histories: Dict[int, ObjectActionHistory] = {}

    def update(
        self,
        interactions: List[HandObjectInteraction],
        timestamp: float
    ) -> List[ActionEvent]:
        """
        Evaluates temporal interaction sequences and emits confirmed ActionEvents.

        Args:
            interactions: Current frame hand-object interaction states.
            timestamp: Frame capture timestamp in seconds.

        Returns:
            List of newly confirmed ActionEvents for this frame.
        """
        emitted_events: List[ActionEvent] = []

        for inter in interactions:
            t_id = inter.track_id
            if t_id not in self.object_histories:
                self.object_histories[t_id] = ObjectActionHistory(t_id, inter.class_name, self.window_size)

            history = self.object_histories[t_id]
            history.append(inter, timestamp)

            # Check action cooldown
            if timestamp - history.last_action_time < self.cooldown:
                continue

            event = self._evaluate_action_rules(history, inter, timestamp)
            if event:
                history.last_action_time = timestamp
                history.last_emitted_action = event.action
                emitted_events.append(event)
                logger.info(f"Emitted ActionEvent: {event.action} on {event.object} (Zone: {event.rack_zone}, Conf: {event.confidence})")

        return emitted_events

    def _evaluate_action_rules(
        self,
        history: ObjectActionHistory,
        current_inter: HandObjectInteraction,
        timestamp: float
    ) -> Optional[ActionEvent]:
        """Evaluates temporal state machine rules to confirm actions."""
        if len(history.interaction_history) < 5:
            return None

        recent_states = [i.interaction_type for i in list(history.interaction_history)[-8:]]
        obj_name = current_inter.class_name
        zone = current_inter.rack_zone

        # 1. PICK ACTION: (IDLE / APPROACH) -> (CONTACT) -> (HOLD_MOVE / CARRYING)
        if current_inter.interaction_type == InteractionType.HOLD_MOVE:
            contact_count = history.count_recent_state(InteractionType.CONTACT, window=8)
            idle_count = history.count_recent_state(InteractionType.IDLE, window=15)
            if contact_count >= 1 or idle_count >= 2:
                history.current_state = "CARRIED_IN_HAND"
                return ActionEvent(
                    action=ActionType.PICK,
                    object=obj_name,
                    actor="astronaut_01",
                    timestamp=round(timestamp, 2),
                    confidence=0.94,
                    rack_zone=zone,
                    status=ActionStatus.CONFIRMED,
                    metadata={"trigger": "temporal_pick_motion"}
                )

        # 2. PLACE ACTION: Was CARRIED_IN_HAND -> Enters Rack Zone -> Hand moves away (IDLE/RELEASE)
        if history.current_state == "CARRIED_IN_HAND" and not current_inter.is_moving:
            if current_inter.interaction_type in [InteractionType.IDLE, InteractionType.APPROACH]:
                history.current_state = "IDLE_ON_RACK"
                return ActionEvent(
                    action=ActionType.PLACE,
                    object=obj_name,
                    actor="astronaut_01",
                    timestamp=round(timestamp, 2),
                    confidence=0.92,
                    rack_zone=zone,
                    status=ActionStatus.CONFIRMED,
                    metadata={"trigger": "temporal_place_deposit"}
                )

        # 3. OPEN / UNCAP ACTION: Static CONTACT on tube/cap for >= 6 frames without gross translation
        if current_inter.interaction_type == InteractionType.CONTACT and not current_inter.is_moving:
            contact_streak = sum(1 for st in recent_states if st == InteractionType.CONTACT)
            if contact_streak >= 5 and history.last_emitted_action != ActionType.OPEN:
                return ActionEvent(
                    action=ActionType.OPEN,
                    object=obj_name,
                    actor="astronaut_01",
                    timestamp=round(timestamp, 2),
                    confidence=0.89,
                    rack_zone=zone,
                    status=ActionStatus.CONFIRMED,
                    metadata={"trigger": "sustained_contact_uncap"}
                )

        # 4. TRANSFER ACTION: Pipette/tool held near tube mouth
        if obj_name == "pipette" and current_inter.interaction_type in [InteractionType.HOLD_MOVE, InteractionType.CONTACT]:
            if zone in ["TRAY", "A1", "A2"]:
                return ActionEvent(
                    action=ActionType.TRANSFER,
                    object="tube_A",
                    actor="astronaut_01",
                    timestamp=round(timestamp, 2),
                    confidence=0.91,
                    rack_zone=zone,
                    status=ActionStatus.CONFIRMED,
                    metadata={"tool": "pipette", "trigger": "fluid_dispense_zone"}
                )

        return None

    def reset(self) -> None:
        """Clears temporal action histories."""
        self.object_histories.clear()
