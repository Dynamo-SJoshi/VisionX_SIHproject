# File: src/schemas/__init__.py
"""
Unified Public Exports for BAS-HAR Schemas (M1, M2, M3).
"""

from .action import (
    ActionEvidence,
    ActionEvent,
    ActionStatus,
    ActionType,
    EventStatus,
    HandType,
    ObjectInteraction,
    RecognitionSource,
    SpatialContext,
)
from .common import (
    BBox,
    SchemaBase,
    utc_now,
)
from .decision import (
    Decision,
    DecisionReason,
    DecisionStatus,
)
from .detection import (
    BoundingBox,
    Detection,
    DetectionFrame,
    Landmark,
)
from .evidence import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceType,
)
from .events import (
    SystemEvent,
    SystemEventType,
)
from .protocol import (
    ExperimentProtocol,
    ProtocolStatus,
    ProtocolStep,
    StepStatus,
    ValidationResult,
)
from .spatial import (
    Point3D,
    SpatialRelation,
    SpatialState,
    ZoneType,
)
from .track import (
    Track,
)

__all__ = [
    # Common
    "BBox",
    "SchemaBase",
    "utc_now",
    # Detection
    "BoundingBox",
    "Landmark",
    "Detection",
    "DetectionFrame",
    # Tracking
    "Track",
    # Spatial
    "Point3D",
    "SpatialRelation",
    "SpatialState",
    "ZoneType",
    # Action
    "ActionEvent",
    "ActionEvidence",
    "ActionStatus",
    "ActionType",
    "EventStatus",
    "HandType",
    "ObjectInteraction",
    "RecognitionSource",
    "SpatialContext",
    # Protocol
    "ExperimentProtocol",
    "ProtocolStatus",
    "ProtocolStep",
    "StepStatus",
    "ValidationResult",
    # Decision
    "Decision",
    "DecisionReason",
    "DecisionStatus",
    # Evidence
    "EvidenceBundle",
    "EvidenceItem",
    "EvidenceType",
    # Events
    "SystemEvent",
    "SystemEventType",
]
