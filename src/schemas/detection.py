# File: src/schemas/detection.py
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """2D Bounding box representation [x1, y1, x2, y2]."""
    x1: float = Field(..., description="Top-left X coordinate")
    y1: float = Field(..., description="Top-left Y coordinate")
    x2: float = Field(..., description="Bottom-right X coordinate")
    y2: float = Field(..., description="Bottom-right Y coordinate")

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def area(self) -> float:
        return self.width * self.height


class Landmark(BaseModel):
    """Pose or Hand landmark keypoint."""
    name: str = Field(..., description="Landmark keypoint identifier name")
    x: float = Field(..., description="X coordinate (normalized 0-1 or pixel)")
    y: float = Field(..., description="Y coordinate (normalized 0-1 or pixel)")
    z: Optional[float] = Field(default=None, description="Depth Z coordinate if available")
    score: float = Field(default=1.0, description="Detection confidence score")


class Detection(BaseModel):
    """Single object detection item."""
    class_name: str = Field(..., description="Detected object class label (e.g. tube_A, cap, pipette)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    bbox: BoundingBox = Field(..., description="Bounding box coordinates")
    track_id: Optional[int] = Field(default=None, description="Persistent tracking ID if tracked")


class DetectionFrame(BaseModel):
    """Container for all object detections, pose, and hand landmarks in a single frame."""
    frame_index: int = Field(default=0, description="Sequential frame index")
    timestamp: float = Field(..., description="Frame capture timestamp in seconds")
    detections: List[Detection] = Field(default_factory=list, description="Object detections")
    pose_landmarks: List[Landmark] = Field(default_factory=list, description="Body pose landmarks")
    left_hand_landmarks: List[Landmark] = Field(default_factory=list, description="Left hand landmarks")
    right_hand_landmarks: List[Landmark] = Field(default_factory=list, description="Right hand landmarks")
