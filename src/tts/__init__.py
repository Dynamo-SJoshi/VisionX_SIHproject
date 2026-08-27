# File: src/tts/__init__.py
"""
Offline text-to-speech module using pyttsx3 with non-blocking fallback.
"""

from .offline_tts import OfflineTTS

__all__ = ["OfflineTTS"]
