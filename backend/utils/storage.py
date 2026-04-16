import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Optional

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evaluations", "interviews.db")


def _init_db() -> None:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interview_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                interview_mode TEXT,
                candidate_name TEXT,
                role_applied TEXT,
                overall_score REAL,
                recommendation TEXT,
                payload_json TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_result(payload: dict[str, Any], interview_mode: Optional[str] = None) -> str:
    """Persist an interview evaluation to SQLite. Returns the DB path."""
    _init_db()
    conn = sqlite3.connect(_DB_PATH)
    try:
        conn.execute(
            """
            INSERT INTO interview_results (
                created_at, interview_mode, candidate_name,
                role_applied, overall_score, recommendation, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(),
                interview_mode,
                payload.get("candidate_name"),
                payload.get("role_applied"),
                payload.get("overall_score"),
                payload.get("recommendation"),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return _DB_PATH
