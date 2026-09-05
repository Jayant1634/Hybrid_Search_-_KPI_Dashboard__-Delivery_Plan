"""SQLite connection and schema. No migration framework, just CREATE TABLE."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT NOT NULL,
        query TEXT NOT NULL,
        latency_ms REAL,
        top_k INTEGER,
        alpha REAL,
        result_count INTEGER,
        error TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT NOT NULL,
        doc_id TEXT NOT NULL,
        relevant INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        severity TEXT NOT NULL,
        message TEXT NOT NULL,
        request_id TEXT
    )
    """,
)


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with WAL mode and a row factory.

    ``path`` may be ``":memory:"`` for tests. Parent directories are created
    for file paths so callers do not have to.
    """

    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create the three tables if they do not already exist."""

    for statement in _SCHEMA:
        conn.execute(statement)
    conn.commit()
