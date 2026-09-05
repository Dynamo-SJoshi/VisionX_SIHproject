"""
BAS-HAR Event Logger.

Implements LoggerInterface and persists SystemEvent objects
to structured JSONL and CSV files.
"""

from __future__ import annotations

import csv
import json
import threading
from collections import deque
from pathlib import Path
from typing import Any, Dict, List

from src.interfaces.logger import LoggerInterface
from src.schemas.events import SystemEvent


class EventLogger(LoggerInterface):
    """
    Thread-safe structured event logger.
    """

    def __init__(
        self,
        log_dir: str = "logs",
        experiment_id: str = "bas_har",
        max_recent_events: int = 500,
    ) -> None:

        self.log_dir = Path(log_dir)
        self.experiment_id = experiment_id

        self.events_dir = self.log_dir / "events"
        self.events_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.jsonl_path = (
            self.events_dir / "events.jsonl"
        )

        self.csv_path = (
            self.events_dir / "events.csv"
        )

        self.max_recent_events = max_recent_events

        self._recent_events: deque[
            Dict[str, Any]
        ] = deque(
            maxlen=max_recent_events
        )

        self._lock = threading.RLock()

        self._csv_initialized = (
            self.csv_path.exists()
            and self.csv_path.stat().st_size > 0
        )

    # ==================================================================
    # LoggerInterface implementation
    # ==================================================================

    def log(
        self,
        event: SystemEvent,
    ) -> None:
        """
        Persist one SystemEvent.
        """

        if not isinstance(event, SystemEvent):
            raise TypeError(
                "EventLogger.log() expects a SystemEvent."
            )

        event_data = event.model_dump(
            mode="json"
        )

        with self._lock:

            # ----------------------------------------------------------
            # JSONL
            # ----------------------------------------------------------

            with self.jsonl_path.open(
                "a",
                encoding="utf-8",
            ) as file:

                file.write(
                    json.dumps(
                        event_data,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

            # ----------------------------------------------------------
            # CSV
            # ----------------------------------------------------------

            self._write_csv(event_data)

            # ----------------------------------------------------------
            # In-memory recent events
            # ----------------------------------------------------------

            self._recent_events.append(
                event_data
            )

    def flush(self) -> None:
        """
        Flush logger state.

        Files are opened/closed on every write, so there are no persistent
        file handles. This method exists to satisfy the interface and
        provide an explicit synchronization point.
        """

        with self._lock:

            self.jsonl_path.touch(
                exist_ok=True
            )

            self.csv_path.touch(
                exist_ok=True
            )

    # ==================================================================
    # CSV
    # ==================================================================

    def _write_csv(
        self,
        event_data: Dict[str, Any],
    ) -> None:
        """
        Write a SystemEvent to CSV.
        """

        row = {
            "event_id": event_data.get(
                "event_id"
            ),

            "event_type": event_data.get(
                "event_type"
            ),

            "timestamp": event_data.get(
                "timestamp"
            ),

            "session_id": event_data.get(
                "session_id"
            ),

            "message": event_data.get(
                "message"
            ),

            "actor_id": event_data.get(
                "actor_id"
            ),

            "action_event_id": event_data.get(
                "action_event_id"
            ),

            "decision_id": event_data.get(
                "decision_id"
            ),

            "step_id": event_data.get(
                "step_id"
            ),

            "confidence": event_data.get(
                "confidence"
            ),

            "data": json.dumps(
                event_data.get(
                    "data",
                    {},
                ),
                ensure_ascii=False,
            ),
        }

        with self.csv_path.open(
            "a",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=row.keys(),
            )

            if not self._csv_initialized:

                writer.writeheader()

                self._csv_initialized = True

            writer.writerow(row)

    # ==================================================================
    # API / DASHBOARD SUPPORT
    # ==================================================================

    def get_recent_events(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Return the most recent events.
        """

        if limit < 1:
            raise ValueError(
                "limit must be at least 1."
            )

        with self._lock:

            events = list(
                self._recent_events
            )

        return events[-limit:]

    def clear_recent_events(self) -> None:
        """
        Clear only the in-memory event buffer.
        """

        with self._lock:
            self._recent_events.clear()

    # ==================================================================
    # Cleanup
    # ==================================================================

    def close(self) -> None:
        """
        Final logger cleanup.
        """

        self.flush()