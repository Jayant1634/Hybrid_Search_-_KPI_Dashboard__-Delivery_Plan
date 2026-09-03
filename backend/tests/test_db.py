import sqlite3
from pathlib import Path

from app.storage.db import connect, init_schema


def test_connect_sets_row_factory_and_wal(tmp_path: Path) -> None:
    conn = connect(tmp_path / "hss.sqlite")
    try:
        assert conn.row_factory is sqlite3.Row
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"
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
