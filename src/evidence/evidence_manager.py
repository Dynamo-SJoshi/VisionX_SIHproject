"""
Evidence Manager for BAS-HAR.

Captures, structures, and persists supporting visual and multi-modal evidence
for action events and critical decisions (e.g. procedure violations).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
import uuid

from src.evidence.snapshot import save_image_frame
from src.interfaces.evidence import EvidenceInterface
from src.schemas.action import ActionEvent
from src.schemas.decision import Decision, DecisionStatus
from src.schemas.evidence import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceType,
)


class EvidenceManager(EvidenceInterface):
    """
    Manages capturing, indexing, and serving visual evidence snapshots.
    """

    def __init__(self, storage_dir: str | Path = "data/evidence/snapshots") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._bundles: List[EvidenceBundle] = []

    def save_frame(self, frame: Any, evidence_id: str) -> Optional[str]:
        """
        Saves an image frame to the evidence snapshot directory.
        Returns the relative file path.
        """
        if frame is None:
            return None

        filename = f"{evidence_id}.jpg"
        output_path = self.storage_dir / filename
        return save_image_frame(frame, output_path)

    def capture_for_action(
        self,
        action_event: ActionEvent,
        frame: Optional[Any] = None,
    ) -> EvidenceBundle:
        """
        Captures and builds an EvidenceBundle for an observed ActionEvent.
        """
        evidence_id = f"ev_act_{uuid.uuid4().hex[:8]}"
        items: List[EvidenceItem] = []

        snapshot_path = None
        if frame is not None:
            snapshot_path = self.save_frame(frame, evidence_id)

        act_name = (
            action_event.action.value
            if hasattr(action_event.action, "value")
            else str(action_event.action)
        )

        item = EvidenceItem(
            evidence_id=f"{evidence_id}_item1",
            evidence_type=EvidenceType.VISUAL,
            timestamp=datetime.now(timezone.utc),
            snapshot_path=snapshot_path,
            description=f"Visual evidence for action '{act_name}' (conf: {action_event.confidence:.2f})",
            confidence=action_event.confidence,
        )
        items.append(item)

        bundle = EvidenceBundle(
            evidence_id=evidence_id,
            action_event_id=action_event.event_id,
            decision_id=None,
            items=items,
        )
        self._bundles.append(bundle)
        return bundle

    def capture_for_decision(
        self,
        decision: Decision,
        frame: Optional[Any] = None,
    ) -> EvidenceBundle:
        """
        Captures and builds an EvidenceBundle for a system Decision (e.g. procedure alert or verification).
        """
        evidence_id = f"ev_dec_{uuid.uuid4().hex[:8]}"
        items: List[EvidenceItem] = []

        snapshot_path = None
        if frame is not None:
            snapshot_path = self.save_frame(frame, evidence_id)

        dec_status_str = (
            decision.status.value
            if hasattr(decision.status, "value")
            else str(decision.status)
        )

        evidence_type = (
            EvidenceType.OPERATOR
            if decision.status == DecisionStatus.PROCEED and "Manual" in decision.message
            else EvidenceType.VISUAL
        )

        item = EvidenceItem(
            evidence_id=f"{evidence_id}_item1",
            evidence_type=evidence_type,
            timestamp=datetime.now(timezone.utc),
            snapshot_path=snapshot_path,
            description=f"Evidence for decision '{dec_status_str}': {decision.message}",
            confidence=decision.confidence,
        )
        items.append(item)

        bundle = EvidenceBundle(
            evidence_id=evidence_id,
            action_event_id=None,
            decision_id=decision.decision_id,
            items=items,
        )
        self._bundles.append(bundle)
        return bundle

    def get_bundle(self, evidence_id: str) -> Optional[EvidenceBundle]:
        """Retrieves an EvidenceBundle by its evidence_id."""
        for b in self._bundles:
            if b.evidence_id == evidence_id:
                return b
        return None
