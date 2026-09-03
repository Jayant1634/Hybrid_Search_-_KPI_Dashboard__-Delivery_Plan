"""Insert and select helpers. Parameterised SQL only."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def insert_request(
    conn: sqlite3.Connection,
    *,
    request_id: str,
    query: str,
    latency_ms: float | None = None,
    top_k: int | None = None,
    alpha: float | None = None,
    result_count: int | None = None,
    error: str | None = None,
    created_at: str | None = None,
) -> int:
    """Insert one row into ``requests`` and return its rowid."""

    cursor = conn.execute(
        """
        INSERT INTO requests
            (request_id, query, latency_ms, top_k, alpha, result_count,
             error, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request_id,
            query,
            latency_ms,
            top_k,
            alpha,
            result_count,
            error,
            created_at or _now(),
        ),
    )
    conn.commit()
    return int(cursor.lastrowid or 0)


def insert_feedback(
    conn: sqlite3.Connection,
    *,
    request_id: str,
    doc_id: str,
    relevant: bool,
    created_at: str | None = None,
) -> int:
    """Insert one row into ``feedback`` and return its rowid."""

    cursor = conn.execute(
        """
        INSERT INTO feedback (request_id, doc_id, relevant, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (request_id, doc_id, int(relevant), created_at or _now()),
    )
    conn.commit()
    return int(cursor.lastrowid or 0)


def insert_log(
    conn: sqlite3.Connection,
    *,
    severity: str,
    message: str,
    request_id: str | None = None,
    created_at: str | None = None,
) -> int:
    """Insert one row into ``logs`` and return its rowid."""

    cursor = conn.execute(
        """
        INSERT INTO logs (created_at, severity, message, request_id)
        VALUES (?, ?, ?, ?)
        """,
        (created_at or _now(), severity, message, request_id),
    )
    conn.commit()
    return int(cursor.lastrowid or 0)


def select_requests(
    conn: sqlite3.Connection, *, limit: int = 100
) -> list[sqlite3.Row]:
    """Return the most recent ``requests`` rows, newest first."""

    cursor = conn.execute(
        "SELECT * FROM requests ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    return cursor.fetchall()


def select_feedback(
    conn: sqlite3.Connection, *, request_id: str | None = None, limit: int = 100
) -> list[sqlite3.Row]:
    """Return ``feedback`` rows, optionally filtered by ``request_id``."""

    if request_id is None:
        cursor = conn.execute(
            "SELECT * FROM feedback ORDER BY id DESC LIMIT ?",
            (limit,),
        )
    else:
        cursor = conn.execute(
            """
            SELECT * FROM feedback
            WHERE request_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (request_id, limit),
        )
    return cursor.fetchall()


def select_logs(
    conn: sqlite3.Connection, *, severity: str | None = None, limit: int = 100
) -> list[sqlite3.Row]:
    """Return ``logs`` rows, optionally filtered by ``severity``."""

    if severity is None:
        cursor = conn.execute(
            "SELECT * FROM logs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
    else:
        cursor = conn.execute(
            "SELECT * FROM logs WHERE severity = ? ORDER BY id DESC LIMIT ?",
            (severity, limit),
        )
    return cursor.fetchall()
