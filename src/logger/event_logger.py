from datetime import datetime, timezone
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
from src.schemas.events import SystemEvent


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

    def log(self, event: Any) -> None:
        """
        Persists a system event as required by LoggerInterface contract.
        Supports SystemEvent instances or generic event dictionaries.
        """
        if isinstance(event, SystemEvent):
            timestamp = event.timestamp.isoformat()
            step_id = event.step_id or ""
            event_type = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
            confidence = event.confidence if event.confidence is not None else 1.0
            alert_type = event.data.get("alert_type", "INFO") if isinstance(event.data, dict) else "INFO"
            record = event.model_dump(mode="json")
        elif isinstance(event, dict):
            timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())
            step_id = event.get("step_id", "")
            event_type = str(event.get("event_type", "UNKNOWN"))
            confidence = float(event.get("confidence", 1.0))
            alert_type = str(event.get("alert_type", "INFO"))
            record = event
        else:
            timestamp = datetime.now(timezone.utc).isoformat()
            step_id = getattr(event, "step_id", "")
            event_type = str(getattr(event, "event_type", type(event).__name__))
            confidence = float(getattr(event, "confidence", 1.0))
            alert_type = str(getattr(event, "alert_type", "INFO"))
            record = getattr(event, "__dict__", {"event": str(event)})

        with self._lock:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp, self.experiment_id, step_id,
                    event_type, alert_type, round(confidence, 3)
                ])

    def flush(self) -> None:
        """
        Flushes buffered logs to persistent storage.
        File I/O operations in EventLogger are atomic with immediate context managers.
        """
        pass

    def log_event(
        self,
        action: Optional[ActionEvent] = None,
        validation: Optional[ValidationResult] = None,
        decision: Optional[Decision] = None,
        *,
        step_id: Optional[str] = None,
        event_type: Optional[str] = None,
        alert_type: Optional[str] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Logs an event to JSON Lines and CSV summary files.
        Supports both:
        1. Direct pipeline schemas: log_event(action, validation, decision)
        2. UI/manual trigger keyword args: log_event(step_id=..., event_type=..., alert_type=..., confidence=..., metadata=...)
        """
        if action is not None and validation is not None and decision is not None:
            # Unpack the Pydantic schemas from pipeline
            timestamp = action.timestamp.isoformat()
            s_id = validation.current_step_id
            e_type = action.action.value if hasattr(action.action, "value") else str(action.action)
            a_type = decision.status.value if hasattr(decision.status, "value") else str(decision.status)
            conf = decision.confidence

            record = {
                "timestamp": timestamp,
                "experiment_id": self.experiment_id,
                "step_id": s_id,
                "event_type": e_type,
                "confidence": conf,
                "alert_type": a_type,
                "action_details": action.model_dump(mode="json"),
                "decision_reason": decision.reason.value if hasattr(decision.reason, "value") else str(decision.reason)
            }
        else:
            # Fallback for manual / keyword step transitions
            timestamp = datetime.now(timezone.utc).isoformat()
            s_id = step_id or ""
            e_type = event_type or "STEP_TRANSITION"
            a_type = alert_type or "OK"
            conf = confidence if confidence is not None else 1.0

            record = {
                "timestamp": timestamp,
                "experiment_id": self.experiment_id,
                "step_id": s_id,
                "event_type": e_type,
                "confidence": conf,
                "alert_type": a_type,
                "metadata": metadata or {},
                **kwargs,
            }

        with self._lock:
            # Append to JSON Lines
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            # Append to CSV Summary
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp, self.experiment_id, s_id,
                    e_type, a_type, round(conf, 3)
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