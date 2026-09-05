"""SQLite connection and schema migrations.

Simple, numbered migrations instead of ``CREATE TABLE IF NOT EXISTS``: each
``NNN_name.sql`` file under ``migrations/`` is a version. A ``schema_version``
table records which versions have run. :func:`migrate` applies every file whose
number is above the current version, each in its own transaction, and
:func:`init_schema` is a thin wrapper that just calls it.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_MIGRATION_RE = re.compile(r"^(\d+)_.*\.sql$")


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


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _discover_migrations(directory: Path) -> list[tuple[int, Path]]:
    """Return ``(version, path)`` for each ``NNN_*.sql`` file, sorted by number."""

    migrations: list[tuple[int, Path]] = []
    for path in directory.glob("*.sql"):
        match = _MIGRATION_RE.match(path.name)
        if match is not None:
            migrations.append((int(match.group(1)), path))
    migrations.sort(key=lambda item: item[0])
    return migrations


def _split_statements(sql: str) -> list[str]:
    """Split a migration file into individual statements on ``;``."""

    return [statement.strip() for statement in sql.split(";") if statement.strip()]


def _current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_version"
    ).fetchone()
    return int(row[0]) if row is not None else 0


def migrate(conn: sqlite3.Connection, migrations_dir: Path | None = None) -> int:
    """Apply every migration above the current version. Return the new version.

    Each migration file runs in its own transaction: on failure the file is
    rolled back and the exception propagates, leaving ``schema_version`` at the
    last file that succeeded. Re-running is a no-op once every file is applied.
    """

    directory = migrations_dir if migrations_dir is not None else _MIGRATIONS_DIR

    previous_isolation = conn.isolation_level
    conn.isolation_level = None  # explicit BEGIN/COMMIT per migration file
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )
        current = _current_version(conn)
        for version, path in _discover_migrations(directory):
            if version <= current:
                continue
            sql = path.read_text(encoding="utf-8")
            try:
                conn.execute("BEGIN")
                for statement in _split_statements(sql):
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO schema_version (version, applied_at) "
                    "VALUES (?, ?)",
                    (version, _now()),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            current = version
        return current
    finally:
        conn.isolation_level = previous_isolation


def init_schema(conn: sqlite3.Connection) -> None:
    """Bring the database up to the latest schema version."""

    migrate(conn)
