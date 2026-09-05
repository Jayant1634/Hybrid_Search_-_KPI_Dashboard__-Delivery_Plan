"""Insert and select helpers. Parameterised SQL only."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from app.observability.metrics import percentile

Granularity = Literal["hour", "day"]


@dataclass(frozen=True)
class KpiSummary:
    total: int
    p50: float
    p95: float
    zero_result_count: int
    error_count: int


@dataclass(frozen=True)
class VolumeBucket:
    bucket: str
    count: int


@dataclass(frozen=True)
class QueryCount:
    query: str
    count: int
    avg_latency_ms: float


@dataclass(frozen=True)
class ZeroResultQuery:
    query: str
    count: int
    last_seen: str


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _bucket_sql(granularity: Granularity) -> str:
    if granularity == "hour":
        return "substr(created_at, 1, 13) || ':00:00'"
    if granularity == "day":
        return "substr(created_at, 1, 10)"
    raise ValueError(f"unknown granularity {granularity!r}; expected 'hour' or 'day'")


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
    client_id: str = "",
) -> int:
    """Insert one row into ``requests`` and return its rowid."""

    cursor = conn.execute(
        """
        INSERT INTO requests
            (request_id, query, latency_ms, top_k, alpha, result_count,
             error, created_at, client_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            client_id,
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
    conn: sqlite3.Connection,
    *,
    severity: str | None = None,
    level: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 100,
) -> list[sqlite3.Row]:
    """Return ``logs`` rows filtered by level and optional time range.

    ``level`` and ``severity`` are the same column; ``level`` wins if both
    are set. ``since`` / ``until`` are inclusive ISO timestamps.
    """

    chosen = level if level is not None else severity
    clauses: list[str] = []
    params: list[object] = []
    if chosen is not None:
        clauses.append("severity = ?")
        params.append(chosen)
    if since is not None:
        clauses.append("created_at >= ?")
        params.append(since)
    if until is not None:
        clauses.append("created_at <= ?")
        params.append(until)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    cursor = conn.execute(
        f"SELECT * FROM logs{where} ORDER BY id DESC LIMIT ?",
        params,
    )
    return cursor.fetchall()


def kpi_summary(conn: sqlite3.Connection, *, since: str) -> KpiSummary:
    """Latency percentiles and counts for ``requests`` at or after ``since``."""

    cursor = conn.execute(
        """
        SELECT latency_ms, result_count, error
        FROM requests
        WHERE created_at >= ?
        """,
        (since,),
    )
    rows = cursor.fetchall()
    latencies = [
        float(row["latency_ms"])
        for row in rows
        if row["latency_ms"] is not None
    ]
    zero_result_count = sum(1 for row in rows if row["result_count"] == 0)
    error_count = sum(1 for row in rows if row["error"])
    return KpiSummary(
        total=len(rows),
        p50=percentile(latencies, 50),
        p95=percentile(latencies, 95),
        zero_result_count=zero_result_count,
        error_count=error_count,
    )


def request_volume(
    conn: sqlite3.Connection,
    *,
    since: str,
    granularity: Granularity = "hour",
) -> list[VolumeBucket]:
    """Request counts per hour or per day at or after ``since``."""

    bucket = _bucket_sql(granularity)
    cursor = conn.execute(
        f"""
        SELECT {bucket} AS bucket, COUNT(*) AS count
        FROM requests
        WHERE created_at >= ?
        GROUP BY bucket
        ORDER BY bucket
        """,
        (since,),
    )
    return [
        VolumeBucket(bucket=str(row["bucket"]), count=int(row["count"]))
        for row in cursor.fetchall()
    ]


def top_queries(
    conn: sqlite3.Connection, *, since: str, limit: int = 10
) -> list[QueryCount]:
    """Most frequent queries since ``since``, with count and average latency."""

    cursor = conn.execute(
        """
        SELECT query, COUNT(*) AS count, AVG(latency_ms) AS avg_latency_ms
        FROM requests
        WHERE created_at >= ?
        GROUP BY query
        ORDER BY count DESC, query ASC
        LIMIT ?
        """,
        (since, limit),
    )
    return [
        QueryCount(
            query=str(row["query"]),
            count=int(row["count"]),
            avg_latency_ms=(
                float(row["avg_latency_ms"])
                if row["avg_latency_ms"] is not None
                else 0.0
            ),
        )
        for row in cursor.fetchall()
    ]


def zero_result_queries(
    conn: sqlite3.Connection, *, since: str, limit: int = 10
) -> list[ZeroResultQuery]:
    """Queries that returned zero hits at or after ``since``."""

    cursor = conn.execute(
        """
        SELECT query, COUNT(*) AS count, MAX(created_at) AS last_seen
        FROM requests
        WHERE created_at >= ? AND result_count = 0
        GROUP BY query
        ORDER BY count DESC, last_seen DESC
        LIMIT ?
        """,
        (since, limit),
    )
    return [
        ZeroResultQuery(
            query=str(row["query"]),
            count=int(row["count"]),
            last_seen=str(row["last_seen"]),
        )
        for row in cursor.fetchall()
    ]

