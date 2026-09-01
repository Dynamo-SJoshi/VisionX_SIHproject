# File: src/spatial/scene.py
from typing import Dict, List, Optional, Tuple
from src.schemas.detection import BoundingBox


class SpatialZone:
    """Represents a named 2D spatial region/slot within the payload or rack area."""

    def __init__(self, name: str, bbox: BoundingBox, description: str = ""):
        self.name = name
        self.bbox = bbox
        self.description = description

    def contains_point(self, point: Tuple[float, float]) -> bool:
        """Checks if a (x, y) point lies within this spatial zone."""
        px, py = point
        return self.bbox.x1 <= px <= self.bbox.x2 and self.bbox.y1 <= py <= self.bbox.y2

    def compute_overlap_ratio(self, other_box: BoundingBox) -> float:
        """Computes overlap ratio of another box within this zone."""
        xA = max(self.bbox.x1, other_box.x1)
        yA = max(self.bbox.y1, other_box.y1)
        xB = min(self.bbox.x2, other_box.x2)
        yB = min(self.bbox.y2, other_box.y2)

        inter_w = max(0.0, xB - xA)
        inter_h = max(0.0, yB - yA)
        inter_area = inter_w * inter_h

        if other_box.area <= 0:
            return 0.0
        return inter_area / other_box.area


class RackSceneLayout:
    """
    Manages the spatial rack slot layout and coordinate frame for on-board experiments.
    Default config defines rack slots (A1, A2, B1, B2) and a workstand tray.
    """

    def __init__(self, frame_width: int = 640, frame_height: int = 480):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.zones: Dict[str, SpatialZone] = {}
        self._init_default_grid()

    def _init_default_grid(self) -> None:
        """Initializes standard rack grid coordinates relative to frame resolution."""
        w, h = self.frame_width, self.frame_height

        # Rack Slot A1 (Top-Left of Rack region)
        self.zones["A1"] = SpatialZone(
            name="A1",
            bbox=BoundingBox(x1=w * 0.55, y1=h * 0.40, x2=w * 0.70, y2=h * 0.65),
            description="Rack Slot A1 (Primary sample tube slot)"
        )
        # Rack Slot A2 (Top-Right of Rack region)
        self.zones["A2"] = SpatialZone(
            name="A2",
            bbox=BoundingBox(x1=w * 0.72, y1=h * 0.40, x2=w * 0.88, y2=h * 0.65),
            description="Rack Slot A2 (Secondary sample tube slot)"
        )
        # Rack Slot B1 (Bottom-Left of Rack region)
        self.zones["B1"] = SpatialZone(
            name="B1",
            bbox=BoundingBox(x1=w * 0.55, y1=h * 0.68, x2=w * 0.70, y2=h * 0.95),
            description="Rack Slot B1 (Storage slot)"
        )
        # Rack Slot B2 (Bottom-Right of Rack region)
        self.zones["B2"] = SpatialZone(
            name="B2",
            bbox=BoundingBox(x1=w * 0.72, y1=h * 0.68, x2=w * 0.88, y2=h * 0.95),
            description="Rack Slot B2 (Storage slot)"
        )
        # Workstand Tray (Left workspace area)
        self.zones["TRAY"] = SpatialZone(
            name="TRAY",
            bbox=BoundingBox(x1=w * 0.05, y1=h * 0.50, x2=w * 0.45, y2=h * 0.95),
            description="Experiment Workstand Tray"
        )

    def get_zone_for_point(self, point: Tuple[float, float]) -> str:
        """Returns the zone name containing the point, or 'FREE_SPACE'."""
        for zone in self.zones.values():
            if zone.contains_point(point):
                return zone.name
        return "FREE_SPACE"

    def get_zone_for_box(self, bbox: BoundingBox) -> str:
        """Returns the best matching zone name for a bounding box based on center or overlap."""
        center_zone = self.get_zone_for_point(bbox.center)
        if center_zone != "FREE_SPACE":
            return center_zone

        # Fallback to largest overlap
        best_zone = "FREE_SPACE"
        best_overlap = 0.25
        for zone in self.zones.values():
            overlap = zone.compute_overlap_ratio(bbox)
            if overlap > best_overlap:
                best_overlap = overlap
                best_zone = zone.name

        return best_zone
