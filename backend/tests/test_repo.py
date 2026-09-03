import sqlite3
from collections.abc import Iterator

import pytest

from app.storage.db import connect, init_schema
from app.storage.repo import (
    insert_feedback,
    insert_log,
    insert_request,
    kpi_summary,
    request_volume,
    select_feedback,
    select_logs,
    select_requests,
    top_queries,
    zero_result_queries,
)


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    connection = connect(":memory:")
    init_schema(connection)
    yield connection
    connection.close()


def test_insert_and_select_request(conn: sqlite3.Connection) -> None:
    rowid = insert_request(
        conn,
        request_id="r1",
        query="hello",
        latency_ms=12.5,
        top_k=10,
        alpha=0.5,
        result_count=3,
    )
    assert rowid > 0
    rows = select_requests(conn)
    assert len(rows) == 1
    assert rows[0]["request_id"] == "r1"
    assert rows[0]["query"] == "hello"
    assert rows[0]["result_count"] == 3
    assert rows[0]["created_at"]


def test_select_requests_newest_first(conn: sqlite3.Connection) -> None:
    insert_request(conn, request_id="a", query="one")
    insert_request(conn, request_id="b", query="two")
    rows = select_requests(conn, limit=1)
    assert len(rows) == 1
    assert rows[0]["request_id"] == "b"


def test_insert_and_select_feedback(conn: sqlite3.Connection) -> None:
    insert_feedback(conn, request_id="r1", doc_id="d1", relevant=True)
    insert_feedback(conn, request_id="r2", doc_id="d2", relevant=False)
    all_rows = select_feedback(conn)
    assert len(all_rows) == 2
    filtered = select_feedback(conn, request_id="r1")
    assert len(filtered) == 1
    assert filtered[0]["doc_id"] == "d1"
    assert filtered[0]["relevant"] == 1


def test_insert_and_select_logs(conn: sqlite3.Connection) -> None:
    insert_log(conn, severity="INFO", message="started")
    insert_log(conn, severity="ERROR", message="boom", request_id="r9")
    errors = select_logs(conn, severity="ERROR")
    assert len(errors) == 1
    assert errors[0]["message"] == "boom"
    assert errors[0]["request_id"] == "r9"
    assert len(select_logs(conn)) == 2


def test_inserts_are_parameterised(conn: sqlite3.Connection) -> None:
    nasty = "'; DROP TABLE requests; --"
    insert_request(conn, request_id=nasty, query=nasty)
    rows = select_requests(conn)
    assert rows[0]["query"] == nasty
    assert conn.execute(
        "SELECT count(*) FROM sqlite_master "
        "WHERE type='table' AND name='requests'"
    ).fetchone()[0] == 1


# Dozen rows with known latencies. Row 12 is before SINCE and must be ignored.
# In-window latencies 10..110 (n=11):
#   p50 rank = 10 * 0.5 = 5.0 -> 60
#   p95 rank = 10 * 0.95 = 9.5 -> 100 + 0.5 * 10 = 105
SINCE = "2026-09-04T00:00:00+00:00"
_DOZEN = (
    ("r01", "volcano", 10.0, 5, None, "2026-09-04T10:05:00+00:00"),
    ("r02", "volcano", 20.0, 3, None, "2026-09-04T10:15:00+00:00"),
    ("r03", "volcano", 30.0, 0, None, "2026-09-04T11:00:00+00:00"),
    ("r04", "bread", 40.0, 2, None, "2026-09-04T11:30:00+00:00"),
    ("r05", "bread", 50.0, 0, None, "2026-09-04T12:00:00+00:00"),
    ("r06", "python", 60.0, 4, None, "2026-09-04T12:10:00+00:00"),
    ("r07", "python", 70.0, 1, "boom", "2026-09-04T12:20:00+00:00"),
    ("r08", "moon", 80.0, 0, None, "2026-09-05T08:00:00+00:00"),
    ("r09", "moon", 90.0, 6, None, "2026-09-05T08:30:00+00:00"),
    ("r10", "jazz", 100.0, 2, None, "2026-09-05T09:00:00+00:00"),
    ("r11", "jazz", 110.0, 0, "fail", "2026-09-05T09:15:00+00:00"),
    ("r12", "old", 1000.0, 8, None, "2026-09-01T00:00:00+00:00"),
)


@pytest.fixture
def seeded(conn: sqlite3.Connection) -> sqlite3.Connection:
    for request_id, query, latency, result_count, error, created_at in _DOZEN:
        insert_request(
            conn,
            request_id=request_id,
            query=query,
            latency_ms=latency,
            result_count=result_count,
            error=error,
            created_at=created_at,
        )
    insert_log(
        conn,
        severity="INFO",
        message="started",
        created_at="2026-09-04T10:00:00+00:00",
    )
    insert_log(
        conn,
        severity="ERROR",
        message="boom",
        request_id="r07",
        created_at="2026-09-04T11:00:00+00:00",
    )
    insert_log(
        conn,
        severity="ERROR",
        message="old error",
        created_at="2026-09-03T10:00:00+00:00",
    )
    insert_log(
        conn,
        severity="INFO",
        message="ok",
        created_at="2026-09-04T12:00:00+00:00",
    )
    insert_log(
        conn,
        severity="ERROR",
        message="later",
        created_at="2026-09-04T13:00:00+00:00",
    )
    insert_log(
        conn,
        severity="WARN",
        message="hmm",
        created_at="2026-09-04T11:30:00+00:00",
    )
    return conn


def test_kpi_summary_since_timestamp(seeded: sqlite3.Connection) -> None:
    summary = kpi_summary(seeded, since=SINCE)
    assert summary.total == 11
    assert summary.p50 == 60.0
    assert summary.p95 == 105.0
    assert summary.zero_result_count == 4
    assert summary.error_count == 2


def test_kpi_summary_empty_window(seeded: sqlite3.Connection) -> None:
    summary = kpi_summary(seeded, since="2026-09-06T00:00:00+00:00")
    assert summary.total == 0
    assert summary.p50 == 0.0
    assert summary.p95 == 0.0
    assert summary.zero_result_count == 0
    assert summary.error_count == 0


def test_volume_per_hour_and_day(seeded: sqlite3.Connection) -> None:
    hourly = request_volume(seeded, since=SINCE, granularity="hour")
    assert [(row.bucket, row.count) for row in hourly] == [
        ("2026-09-04T10:00:00", 2),
        ("2026-09-04T11:00:00", 2),
        ("2026-09-04T12:00:00", 3),
        ("2026-09-05T08:00:00", 2),
        ("2026-09-05T09:00:00", 2),
    ]
    daily = request_volume(seeded, since=SINCE, granularity="day")
    assert [(row.bucket, row.count) for row in daily] == [
        ("2026-09-04", 7),
        ("2026-09-05", 4),
    ]


def test_volume_rejects_unknown_granularity(seeded: sqlite3.Connection) -> None:
    with pytest.raises(ValueError, match="granularity"):
        request_volume(seeded, since=SINCE, granularity="week")  # type: ignore[arg-type]


def test_top_queries_count_and_avg_latency(seeded: sqlite3.Connection) -> None:
    rows = top_queries(seeded, since=SINCE)
    assert [(row.query, row.count, row.avg_latency_ms) for row in rows] == [
        ("volcano", 3, 20.0),
        ("bread", 2, 45.0),
        ("jazz", 2, 105.0),
        ("moon", 2, 85.0),
        ("python", 2, 65.0),
    ]
    limited = top_queries(seeded, since=SINCE, limit=1)
    assert len(limited) == 1
    assert limited[0].query == "volcano"


def test_zero_result_queries(seeded: sqlite3.Connection) -> None:
    rows = zero_result_queries(seeded, since=SINCE)
    assert [(row.query, row.count, row.last_seen) for row in rows] == [
        ("jazz", 1, "2026-09-05T09:15:00+00:00"),
        ("moon", 1, "2026-09-05T08:00:00+00:00"),
        ("bread", 1, "2026-09-04T12:00:00+00:00"),
        ("volcano", 1, "2026-09-04T11:00:00+00:00"),
    ]


def test_logs_filtered_by_level_and_time_range(seeded: sqlite3.Connection) -> None:
    rows = select_logs(
        seeded,
        level="ERROR",
        since="2026-09-04T00:00:00+00:00",
        until="2026-09-04T12:00:00+00:00",
    )
    assert [row["message"] for row in rows] == ["boom"]
    assert rows[0]["request_id"] == "r07"

