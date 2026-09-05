"""JSON logging: one object per line, safe to configure twice.

``configure`` attaches a JSON stdout handler and, when given a SQLite
connection, a ``SqliteLogHandler`` that persists every record that reaches
the handler (subject to the root logger level) to the ``logs`` table so
the debug page can read them back.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from datetime import datetime, timezone

from app.storage.repo import insert_log

_JSON_FLAG = "_hss_json_configured"
_DB_FLAG = "_hss_db_configured"

_RESERVED = frozenset(
    logging.makeLogRecord({}).__dict__.keys()
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """Render a log record as a single-line JSON object.

    Emits ``ts`` (ISO-8601 UTC), ``level``, ``logger`` and ``message`` keys,
    then merges any non-reserved attributes passed via ``extra=``.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class SqliteLogHandler(logging.Handler):
    """Persist every record that reaches this handler to the ``logs`` table.

    Each emitted record becomes one row (severity, message, ``request_id`` if
    it was passed via ``extra=``). Insert failures are routed through
    ``handleError`` so logging never crashes the caller. The default level is
    ``NOTSET`` so INFO/DEBUG are stored when the root logger allows them.
    """

    def __init__(
        self, conn: sqlite3.Connection, level: int = logging.NOTSET
    ) -> None:
        super().__init__(level)
        self._conn = conn

    def emit(self, record: logging.LogRecord) -> None:
        try:
            insert_log(
                self._conn,
                severity=record.levelname,
                message=record.getMessage(),
                request_id=getattr(record, "request_id", None),
            )
        except Exception:
            self.handleError(record)


def _find_flagged(root: logging.Logger, flag: str) -> logging.Handler | None:
    for handler in root.handlers:
        if getattr(handler, flag, False):
            return handler
    return None


def configure(
    level: int | str = logging.INFO,
    *,
    db: sqlite3.Connection | None = None,
) -> None:
    """Attach the JSON stdout handler and, if ``db`` is given, the DB handler.

    Safe to call more than once: repeated calls reuse the existing handlers
    (refreshing the JSON level and the DB connection) instead of adding
    duplicates, so log lines are never doubled.
    """

    root = logging.getLogger()
    root.setLevel(level)

    json_handler = _find_flagged(root, _JSON_FLAG)
    if json_handler is None:
        json_handler = logging.StreamHandler(sys.stdout)
        json_handler.setFormatter(JsonFormatter())
        setattr(json_handler, _JSON_FLAG, True)
        root.addHandler(json_handler)
    json_handler.setLevel(level)

    if db is not None:
        db_handler = _find_flagged(root, _DB_FLAG)
        if db_handler is None:
            db_handler = SqliteLogHandler(db)
            setattr(db_handler, _DB_FLAG, True)
            root.addHandler(db_handler)
        elif isinstance(db_handler, SqliteLogHandler):
            db_handler._conn = db
