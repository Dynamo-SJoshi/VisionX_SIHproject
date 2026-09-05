# File: src/spatial/scene.py
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

from src.schemas.detection import BoundingBox

logger = logging.getLogger(__name__)


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
    Manages the spatial rack slot layout and coordinate frame.
    Supports importing custom layouts from external JSON configs, calibrating from JPG images,
    or falling back to dynamic relative workspace positioning.
    """

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        layout_config_path: Optional[Union[str, Path]] = None
    ):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.zones: Dict[str, SpatialZone] = {}
        self.custom_layout_loaded = False

        if layout_config_path and Path(layout_config_path).exists():
            self.load_from_json(layout_config_path)

    def load_from_json(self, config_path: Union[str, Path]) -> bool:
        """
        Loads custom rack zones from an external JSON file.
        Format:
        {
          "zones": [
            {"name": "Slot_1", "bbox": [x1, y1, x2, y2], "description": "Primary bay"},
            {"name": "Tool_Holder", "bbox": [x1, y1, x2, y2], "description": "Screwdriver/Tool rack"}
          ]
        }
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.zones.clear()
            for z in data.get("zones", []):
                name = z["name"]
                coords = z["bbox"]  # [x1, y1, x2, y2]
                bbox = BoundingBox(x1=coords[0], y1=coords[1], x2=coords[2], y2=coords[3])
                desc = z.get("description", "")
                self.zones[name] = SpatialZone(name=name, bbox=bbox, description=desc)

            self.custom_layout_loaded = True
            logger.info(f"Loaded {len(self.zones)} custom rack zones from {config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load custom rack layout from {config_path}: {e}")
            return False

    def load_from_image_calibration(self, image_path: Union[str, Path], zones_dict: Dict[str, List[float]]) -> bool:
        """
        Imports a custom rack layout defined on top of a reference JPG/PNG image.
        
        Args:
            image_path: Path to reference JPG of the rack.
            zones_dict: Dict mapping zone_name -> [x1, y1, x2, y2] pixel coordinates.
        """
        try:
            import cv2
            img = cv2.imread(str(image_path))
            if img is not None:
                self.frame_height, self.frame_width = img.shape[:2]

            self.zones.clear()
            for name, coords in zones_dict.items():
                bbox = BoundingBox(x1=coords[0], y1=coords[1], x2=coords[2], y2=coords[3])
                self.zones[name] = SpatialZone(name=name, bbox=bbox)

            self.custom_layout_loaded = True
            logger.info(f"Imported {len(self.zones)} zones calibrated from image: {image_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to calibrate rack layout from image {image_path}: {e}")
            return False

    def get_zone_for_point(self, point: Tuple[float, float]) -> str:
        """Returns zone name containing the point, or dynamic relative position."""
        if self.custom_layout_loaded and self.zones:
            for zone in self.zones.values():
                if zone.contains_point(point):
                    return zone.name

        # Fallback to dynamic relative quadrant (e.g. "WORKSPACE_LEFT", "WORKSPACE_RIGHT")
        px, py = point
        col = "LEFT" if px < self.frame_width * 0.5 else "RIGHT"
        row = "UPPER" if py < self.frame_height * 0.5 else "LOWER"
        return f"{row}_{col}"

    def get_zone_for_box(self, bbox: BoundingBox) -> str:
        """Returns matching custom zone or dynamic relative workspace position."""
        if self.custom_layout_loaded and self.zones:
            center_zone = self.get_zone_for_point(bbox.center)
            if center_zone in self.zones:
                return center_zone

            # Check overlap
            best_zone = None
            best_overlap = 0.25
            for zone in self.zones.values():
                overlap = zone.compute_overlap_ratio(bbox)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_zone = zone.name

            if best_zone:
                return best_zone

        return self.get_zone_for_point(bbox.center)
