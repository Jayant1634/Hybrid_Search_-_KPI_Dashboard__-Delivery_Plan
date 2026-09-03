"""Dashboard reads under ``/api/dashboard``.

KPI endpoints take a ``window`` like ``24h`` or ``7d``. List endpoints take
``limit``, capped at 100. ``GET /experiments`` returns the rows of
``experiments.csv``, or an empty list if the file is missing.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import load_config
from app.storage.db import connect
from app.storage.repo import (
    kpi_summary,
    request_volume,
    select_logs,
    top_queries,
    zero_result_queries,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_WINDOW = re.compile(r"^(\d+)([hd])$")
_CSV_NAME = "experiments.csv"
_MAX_LIMIT = 100
Limit = Annotated[int, Query(ge=1, le=_MAX_LIMIT)]


class KpiSummaryResponse(BaseModel):
    total: int
    p50: float
    p95: float
    zero_result_count: int
    error_count: int


class VolumePoint(BaseModel):
    bucket: str
    count: int


class TopQuery(BaseModel):
    query: str
    count: int
    avg_latency_ms: float


class ZeroResultQuery(BaseModel):
    query: str
    count: int
    last_seen: str


class LogEntry(BaseModel):
    created_at: str
    severity: str
    message: str
    request_id: str | None


def parse_window(window: str) -> tuple[str, Literal["hour", "day"]]:
    """Return ``(since_iso, granularity)`` for a ``24h`` / ``7d`` window."""

    match = _WINDOW.fullmatch(window.strip().lower())
    if match is None:
        raise HTTPException(
            status_code=422,
            detail="window must look like 24h or 7d",
        )
    amount = int(match.group(1))
    if amount < 1:
        raise HTTPException(
            status_code=422,
            detail="window amount must be at least 1",
        )
    unit = match.group(2)
    now = datetime.now(timezone.utc)
    delta = timedelta(hours=amount) if unit == "h" else timedelta(days=amount)
    since = (now - delta).isoformat()
    granularity: Literal["hour", "day"] = "hour" if unit == "h" else "day"
    return since, granularity


@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    """Open a short-lived connection so handlers are not thread-bound."""

    conn = connect(load_config().sqlite_path)
    try:
        yield conn
    finally:
        conn.close()


def _read_experiments() -> list[dict[str, str]]:
    path = load_config().metrics_dir / _CSV_NAME
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@router.get("/kpi/summary", response_model=KpiSummaryResponse)
def dashboard_kpi_summary(window: str = "24h") -> KpiSummaryResponse:
    since, _granularity = parse_window(window)
    with _db() as conn:
        summary = kpi_summary(conn, since=since)
    return KpiSummaryResponse(
        total=summary.total,
        p50=summary.p50,
        p95=summary.p95,
        zero_result_count=summary.zero_result_count,
        error_count=summary.error_count,
    )


@router.get("/kpi/volume", response_model=list[VolumePoint])
def dashboard_kpi_volume(window: str = "24h") -> list[VolumePoint]:
    since, granularity = parse_window(window)
    with _db() as conn:
        rows = request_volume(conn, since=since, granularity=granularity)
    return [VolumePoint(bucket=row.bucket, count=row.count) for row in rows]


@router.get("/kpi/top-queries", response_model=list[TopQuery])
def dashboard_kpi_top_queries(
    window: str = "24h",
    limit: Limit = 10,
) -> list[TopQuery]:
    since, _granularity = parse_window(window)
    with _db() as conn:
        rows = top_queries(conn, since=since, limit=limit)
    return [
        TopQuery(
            query=row.query,
            count=row.count,
            avg_latency_ms=row.avg_latency_ms,
        )
        for row in rows
    ]


@router.get("/kpi/zero-results", response_model=list[ZeroResultQuery])
def dashboard_kpi_zero_results(
    window: str = "24h",
    limit: Limit = 10,
) -> list[ZeroResultQuery]:
    since, _granularity = parse_window(window)
    with _db() as conn:
        rows = zero_result_queries(conn, since=since, limit=limit)
    return [
        ZeroResultQuery(
            query=row.query,
            count=row.count,
            last_seen=row.last_seen,
        )
        for row in rows
    ]


@router.get("/experiments")
def dashboard_experiments() -> list[dict[str, str]]:
    return _read_experiments()


@router.get("/logs", response_model=list[LogEntry])
def dashboard_logs(
    window: str = "24h",
    level: str | None = None,
    limit: Limit = 100,
) -> list[LogEntry]:
    since, _granularity = parse_window(window)
    with _db() as conn:
        rows = select_logs(conn, level=level, since=since, limit=limit)
    return [
        LogEntry(
            created_at=str(row["created_at"]),
            severity=str(row["severity"]),
            message=str(row["message"]),
            request_id=row["request_id"],
        )
        for row in rows
    ]
