# File: src/camera/__init__.py
"""
Camera capture module supporting USB/RTSP inputs and synthetic fallback feed.
"""

from .capture import CameraCapture

__all__ = ["CameraCapture"]
