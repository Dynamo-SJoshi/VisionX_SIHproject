import csv
import json
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

# Import the interface and schemas to ensure contract compliance
from src.interfaces.logger import LoggerInterface
from src.schemas.action import ActionEvent
from src.schemas.protocol import ValidationResult
from src.schemas.decision import Decision


class EventLogger(LoggerInterface):
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

    def log_event(self, action: ActionEvent, validation: ValidationResult, decision: Decision) -> None:
        """
        Logs a complete pipeline cycle to JSON Lines and CSV summary files.
        Unpacks Pydantic schemas to match the expected flat structure.
        """
        # Unpack the Pydantic schemas
        timestamp = action.timestamp.isoformat()
        step_id = validation.current_step_id
        event_type = action.action.value
        alert_type = decision.status.value
        confidence = decision.confidence

        # Build the structured record
        record = {
            "timestamp": timestamp,
            "experiment_id": self.experiment_id,
            "step_id": step_id,
            "event_type": event_type,
            "confidence": confidence,
            "alert_type": alert_type,
            "action_details": action.model_dump(mode='json'),
            "decision_reason": decision.reason.value
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
                
        print(f"[LOGGER] Event saved to {self.jsonl_path}")

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