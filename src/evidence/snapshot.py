"""
Snapshot capture and visual annotation utility for BAS-HAR evidence subsystem.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional


def save_image_frame(
    frame: Any,
    output_path: str | Path,
    title: Optional[str] = None,
) -> Optional[str]:
    """
    Saves an image frame (numpy array, PIL Image, or raw bytes) to disk.
    Creates parent directories if necessary.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if frame is None:
        return None

    try:
        # Check for PIL Image
        if hasattr(frame, "save"):
            frame.save(str(path))
            return str(path)

        # Check for OpenCV / numpy ndarray
        if hasattr(frame, "shape"):
            try:
                import cv2
                cv2.imwrite(str(path), frame)
                return str(path)
            except ImportError:
                # Try Pillow fallback for numpy
                try:
                    from PIL import Image
                    img = Image.fromarray(frame)
                    img.save(str(path))
                    return str(path)
                except Exception:
                    pass

        # Check for bytes / bytearray
        if isinstance(frame, (bytes, bytearray)):
            with open(path, "wb") as f:
                f.write(frame)
            return str(path)

    except Exception as e:
        print(f"[EVIDENCE] Warning: Failed to save frame to {path}: {e}")
        return None

    return None
