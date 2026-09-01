# File: src/schemas/action.py
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Standardized action vocabulary for M2 perception events."""
    IDENTIFY = "IDENTIFY"
    PICK = "PICK"
    OPEN = "OPEN"
    TRANSFER = "TRANSFER"
    SEAL = "SEAL"
    PLACE = "PLACE"


class ActionStatus(str, Enum):
    """Uncertainty classification status."""
    CONFIRMED = "CONFIRMED"
    UNCERTAIN = "UNCERTAIN"


class ActionEvent(BaseModel):
    """
    Standardized M2 Action Event output passed to the Protocol Engine.
    
    Example:
    {
      "action": "PICK",
      "object": "tube_A",
      "actor": "astronaut_01",
      "timestamp": 12.43,
      "confidence": 0.93,
      "rack_zone": "A2",
      "status": "CONFIRMED"
    }
    """
    action: ActionType = Field(..., description="Observed action from vocabulary")
    object: str = Field(..., description="Target object identifier (e.g. tube_A, cap)")
    actor: str = Field(default="astronaut_01", description="Actor performing the action")
    timestamp: float = Field(..., description="Timestamp in seconds from video start or UTC epoch")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    rack_zone: Optional[str] = Field(default=None, description="Spatial rack zone reference")
    status: ActionStatus = Field(default=ActionStatus.CONFIRMED, description="Event uncertainty status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional spatial or pose metrics")
