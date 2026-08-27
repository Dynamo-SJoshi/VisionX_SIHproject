# File: src/tts/offline_tts.py
import logging
import queue
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class OfflineTTS:
    """Offline Text-to-Speech synthesizer running asynchronously in a background thread."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.speech_queue: queue.Queue = queue.Queue()
        self.engine = None
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False

        if self.enabled:
            self._init_engine()

    def _init_engine(self) -> None:
        """Initializes pyttsx3 engine and starts background processing thread."""
        try:
            import pyttsx3
            # Try initializing engine
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 160)
            self.engine.setProperty("volume", 0.9)
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logger.info("pyttsx3 Offline TTS engine initialized successfully.")
        except Exception as e:
            logger.warning(f"Failed to initialize pyttsx3 TTS engine ({e}). Falling back to log output.")
            self.enabled = False

    def _worker_loop(self) -> None:
        """Background thread worker reading messages from queue and speaking them."""
        while self.running:
            try:
                text = self.speech_queue.get(timeout=0.5)
                if text is None:
                    break
                if self.engine:
                    self.engine.say(text)
                    self.engine.runAndWait()
                self.speech_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in TTS speech worker: {e}")

    def speak(self, text: str) -> None:
        """
        Enqueues a text prompt for speech synthesis. Non-blocking call.
        """
        logger.info(f"[TTS ANNOUNCEMENT]: {text}")
        if self.enabled and self.running:
            self.speech_queue.put(text)

    def stop(self) -> None:
        """Stops the TTS worker thread."""
        self.running = False
        if self.enabled:
            self.speech_queue.put(None)
