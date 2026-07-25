"""Minimal SQLite persistence for completed and skipped incident runs."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class IncidentRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_runs (
                    incident_id TEXT PRIMARY KEY,
                    scenario_id TEXT,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.commit()
        finally:
            connection.close()

    def save(self, run: dict[str, Any]) -> None:
        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT OR REPLACE INTO incident_runs
                (incident_id, scenario_id, created_at, status, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run["incident_id"],
                    run.get("scenario_id"),
                    datetime.now(UTC).isoformat(),
                    run["status"],
                    json.dumps(run),
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def list_recent(self) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT payload FROM incident_runs ORDER BY created_at DESC"
            ).fetchall()
        finally:
            connection.close()
        return [json.loads(row["payload"]) for row in rows]

    def get(self, incident_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT payload FROM incident_runs WHERE incident_id = ?", (incident_id,)
            ).fetchone()
        finally:
            connection.close()
        return json.loads(row["payload"]) if row else None
