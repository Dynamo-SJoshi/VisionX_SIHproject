"""
SQLite Structured Audit Logger for BAS-HAR.

Provides persistent, queryable, ACID-compliant storage for all experiment events,
decisions, evidence links, and operator overrides.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from src.interfaces.logger import LoggerInterface
from src.schemas.action import ActionEvent
from src.schemas.decision import Decision
from src.schemas.protocol import ValidationResult


class SQLiteLogger(LoggerInterface):
    """
    Thread-safe SQLite logger storing chronological experiment audit trails.
    """

    def __init__(self, db_path: str | Path = "data/logs/bas_events.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a connection with Row factory enabled."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes tables for sessions, events, decisions, and evidence."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 1. Sessions Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    experiment_id TEXT NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL,
                    status TEXT NOT NULL,
                    metadata_json TEXT
                )
                """
            )

            # 2. Audit Trail Events Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    event_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    validation_status TEXT NOT NULL,
                    decision_status TEXT NOT NULL,
                    decision_reason TEXT,
                    message TEXT NOT NULL,
                    evidence_id TEXT,
                    snapshot_path TEXT,
                    raw_event_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_session ON audit_events (session_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON audit_events (timestamp)"
            )

            conn.commit()
            conn.close()

    def start_session(
        self, session_id: str, experiment_id: str, start_time: float, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Records the start of an experiment session."""
        with self._lock:
            conn = self._get_connection()
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions (session_id, experiment_id, start_time, status, metadata_json)
                VALUES (?, ?, ?, 'ACTIVE', ?)
                """,
                (session_id, experiment_id, start_time, json.dumps(metadata or {})),
            )
            conn.commit()
            conn.close()

    def stop_session(self, session_id: str, end_time: float) -> None:
        """Marks a session as completed."""
        with self._lock:
            conn = self._get_connection()
            conn.execute(
                """
                UPDATE sessions SET end_time = ?, status = 'COMPLETED'
                WHERE session_id = ?
                """,
                (end_time, session_id),
            )
            conn.commit()
            conn.close()

    def log(self, event: Any) -> None:
        """Implements generic LoggerInterface log method."""
        pass

    def log_pipeline_event(
        self,
        session_id: str,
        action: ActionEvent,
        validation: ValidationResult,
        decision: Decision,
        evidence_id: Optional[str] = None,
        snapshot_path: Optional[str] = None,
    ) -> int:
        """
        Logs an atomic pipeline cycle with full audit details into SQLite.
        Returns the inserted record ID.
        """
        act_str = action.action.value if hasattr(action.action, "value") else str(action.action)
        val_status_str = (
            validation.status.value if hasattr(validation.status, "value") else str(validation.status)
        )
        dec_status_str = (
            decision.status.value if hasattr(decision.status, "value") else str(decision.status)
        )
        dec_reason_str = (
            decision.reason.value if hasattr(decision.reason, "value") else str(decision.reason)
        )

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_events (
                    session_id, timestamp, event_id, step_id, action,
                    confidence, validation_status, decision_status, decision_reason,
                    message, evidence_id, snapshot_path, raw_event_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    action.timestamp.timestamp(),
                    action.event_id,
                    validation.current_step_id,
                    act_str,
                    round(action.confidence, 4),
                    val_status_str,
                    dec_status_str,
                    dec_reason_str,
                    decision.message,
                    evidence_id,
                    snapshot_path,
                    action.model_dump_json(),
                ),
            )
            record_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return record_id

    def flush(self) -> None:
        """No-op for SQLite as transactions are committed on insert."""
        pass

    def get_session_events(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Queries events for a specific session joined with experiment info ordered chronologically."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT a.*, COALESCE(s.experiment_id, 'unknown_experiment') AS experiment_id
                FROM audit_events a
                LEFT JOIN sessions s ON a.session_id = s.session_id
                WHERE a.session_id = ?
                ORDER BY a.timestamp ASC
                LIMIT ? OFFSET ?
                """,
                (session_id, limit, offset),
            )
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            conn.close()
            return results

    def export_session_csv(self, session_id: str, output_csv_path: str | Path) -> str:
        """Exports a session's audit log to a formatted CSV file."""
        events = self.get_session_events(session_id, limit=10000)
        path = Path(output_csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "id",
            "session_id",
            "experiment_id",
            "timestamp",
            "event_id",
            "step_id",
            "action",
            "confidence",
            "validation_status",
            "decision_status",
            "decision_reason",
            "message",
            "evidence_id",
            "snapshot_path",
            "created_at",
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(events)

        return str(path)
