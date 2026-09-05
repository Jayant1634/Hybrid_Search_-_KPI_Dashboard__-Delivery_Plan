import shutil
import sqlite3
import threading
from pathlib import Path

from app.storage import db as db_module
from app.storage.db import connect, init_schema, migrate
from app.storage.repo import insert_request, select_requests

_MIGRATIONS = Path(db_module.__file__).parent / "migrations"


def _version(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_version"
    ).fetchone()[0]


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def test_connect_sets_row_factory_and_wal(tmp_path: Path) -> None:
    conn = connect(tmp_path / "hss.sqlite")
    try:
        assert conn.row_factory is sqlite3.Row
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"
    finally:
        conn.close()


def test_connect_allows_other_thread(tmp_path: Path) -> None:
    conn = connect(tmp_path / "hss.sqlite")
    errors: list[BaseException] = []

    def _query() -> None:
        try:
            conn.execute("SELECT 1")
        except BaseException as exc:
            errors.append(exc)

    try:
        thread = threading.Thread(target=_query)
        thread.start()
        thread.join()
        assert errors == []
    finally:
        conn.close()


def test_connect_creates_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "deep" / "hss.sqlite"
    conn = connect(target)
    try:
        assert target.parent.is_dir()
    finally:
        conn.close()


def test_init_schema_creates_three_tables() -> None:
    conn = connect(":memory:")
    try:
        init_schema(conn)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = {row["name"] for row in rows}
        assert {"requests", "feedback", "logs"} <= names
        assert "client_id" in _columns(conn, "requests")
    finally:
        conn.close()


def test_init_schema_is_idempotent() -> None:
    conn = connect(":memory:")
    try:
        init_schema(conn)
        init_schema(conn)
        count = conn.execute(
            "SELECT count(*) FROM sqlite_master "
            "WHERE type='table' AND name='requests'"
        ).fetchone()[0]
        assert count == 1
    finally:
        conn.close()


def test_fresh_db_migrates_to_version_2_with_client_id() -> None:
    conn = connect(":memory:")
    try:
        assert migrate(conn) == 2
        assert _version(conn) == 2
        assert "client_id" in _columns(conn, "requests")
    finally:
        conn.close()


def test_db_built_from_001_only_upgrades_and_takes_insert(tmp_path: Path) -> None:
    v1_only = tmp_path / "migrations"
    v1_only.mkdir()
    shutil.copy(_MIGRATIONS / "001_initial.sql", v1_only / "001_initial.sql")

    conn = connect(":memory:")
    try:
        # A database that only knows migration 001: v1 schema, no client_id.
        assert migrate(conn, v1_only) == 1
        assert "client_id" not in _columns(conn, "requests")

        # The real migration set brings it up to v2 with the column.
        assert migrate(conn) == 2
        assert "client_id" in _columns(conn, "requests")

        rowid = insert_request(
            conn, request_id="r1", query="hello", client_id="web"
        )
        assert rowid > 0
        rows = select_requests(conn)
        assert rows[0]["client_id"] == "web"
    finally:
        conn.close()


def test_migrate_twice_is_a_noop() -> None:
    conn = connect(":memory:")
    try:
        first = migrate(conn)
        applied_first = conn.execute(
            "SELECT count(*) FROM schema_version"
        ).fetchone()[0]

        second = migrate(conn)
        applied_second = conn.execute(
            "SELECT count(*) FROM schema_version"
        ).fetchone()[0]

        assert first == second == 2
        assert applied_first == applied_second == 2
    finally:
        conn.close()
