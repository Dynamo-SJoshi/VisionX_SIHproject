"""
Logging interface for BAS-HAR.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.schemas.events import SystemEvent


class LoggerInterface(ABC):
    """
    Contract for BAS-HAR event loggers.
    """

    @abstractmethod
    def log(
        self,
        event: SystemEvent,
    ) -> None:
        """
        Persist a system event.

        Implementations may write to:
            JSONL
            CSV
            SQLite
            console
            remote storage
        """
        raise NotImplementedError

    @abstractmethod
    def flush(self) -> None:
        """
        Flush buffered logs to persistent storage.
        """
        raise NotImplementedError

    def close(self) -> None:
        """
        Optional cleanup hook.

        Concrete implementations can override this.
        """
        self.flush()

    def name(self) -> str:
        """
        Human-readable logger name.
        """
        return self.__class__.__name__