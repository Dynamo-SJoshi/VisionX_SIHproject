# File: src/logger/event_logger.py
import csv
import json
import os
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional


class EventLogger:
    """Thread-safe event logger writing JSON Lines and CSV experiment summaries."""

    def __init__(self, log_dir: str = "logs", experiment_id: str = "sample_transfer_v1"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.experiment_id = experiment_id
        self.jsonl_path = self.log_dir / "events.jsonl"
        self.csv_path = self.log_dir / "summary.csv"
        self._lock = threading.Lock()

        self._init_csv()

    def _init_csv(self) -> None:
        """Ensures CSV summary file has header row."""
        with self._lock:
            if not self.csv_path.exists():
                with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "timestamp", "experiment_id", "step_id",
                        "event_type", "alert_type", "confidence"
                    ])

    def log_event(
        self,
        step_id: str,
        event_type: str,
        alert_type: str = "OK",
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Logs an observed event to JSON Lines and CSV summary files.
        """
        import datetime
        if timestamp is None:
            timestamp = datetime.datetime.now().isoformat()

        if metadata is None:
            metadata = {}

        record = {
            "timestamp": timestamp,
            "experiment_id": self.experiment_id,
            "step_id": step_id,
            "event_type": event_type,
            "confidence": confidence,
            "alert_type": alert_type,
            "metadata": metadata
        }

        with self._lock:
            # Append to JSON Lines
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            # Append to CSV Summary
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp, self.experiment_id, step_id,
                    event_type, alert_type, round(confidence, 3)
                ])

        return record

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns the most recent logged events from the JSON Lines file."""
        events = []
        with self._lock:
            if not self.jsonl_path.exists():
                return []

            with open(self.jsonl_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

        return list(reversed(events))
