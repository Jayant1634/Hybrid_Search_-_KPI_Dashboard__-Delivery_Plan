import sqlite3
from collections.abc import Iterator

import pytest

from app.storage.db import connect, init_schema
from app.storage.repo import (
    insert_feedback,
    insert_log,
    insert_request,
    select_feedback,
    select_logs,
    select_requests,
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
