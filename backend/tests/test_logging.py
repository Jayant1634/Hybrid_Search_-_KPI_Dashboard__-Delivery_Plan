import json
import logging
from collections.abc import Iterator

import pytest

from app.observability.logging import JsonFormatter, configure
from app.storage.db import connect, init_schema
from app.storage.repo import select_logs


def _format(record: logging.LogRecord) -> dict:
    return json.loads(JsonFormatter().format(record))


def test_core_fields_present() -> None:
    record = logging.LogRecord(
        name="svc", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello %s", args=("world",), exc_info=None,
    )
    obj = _format(record)
    assert obj["level"] == "INFO"
    assert obj["logger"] == "svc"
    assert obj["message"] == "hello world"
    assert "ts" in obj


def test_extra_fields_end_up_in_json() -> None:
    record = logging.LogRecord(
        name="svc", level=logging.INFO, pathname=__file__, lineno=1,
        msg="query", args=(), exc_info=None,
    )
    record.query_id = "abc123"
    record.latency_ms = 42
    obj = _format(record)
    assert obj["query_id"] == "abc123"
    assert obj["latency_ms"] == 42


def test_one_json_object_per_line() -> None:
    record = logging.LogRecord(
        name="svc", level=logging.WARNING, pathname=__file__, lineno=1,
        msg="line", args=(), exc_info=None,
    )
    line = JsonFormatter().format(record)
    assert "\n" not in line
    json.loads(line)


def test_configure_is_safe_to_call_twice(
    _isolate_root_handlers: None,
) -> None:
    root = logging.getLogger()
    before = list(root.handlers)
    configure(logging.DEBUG)
    configure(logging.INFO)
    added = [h for h in root.handlers if h not in before]
    assert len(added) == 1
    assert added[0].level == logging.INFO


@pytest.fixture
def _isolate_root_handlers() -> Iterator[None]:
    root = logging.getLogger()
    before = list(root.handlers)
    try:
        yield
    finally:
        for handler in root.handlers:
            if handler not in before:
                root.removeHandler(handler)


def test_info_and_above_land_in_logs_table(
    _isolate_root_handlers: None,
) -> None:
    conn = connect(":memory:")
    init_schema(conn)
    try:
        configure(logging.INFO, db=conn)
        logger = logging.getLogger("svc")
        logger.debug("too quiet for INFO root")
        logger.info("hello")
        logger.warning("careful now")
        logger.error("boom", extra={"request_id": "r1"})

        rows = select_logs(conn)
        severities = {row["severity"] for row in rows}
        assert severities == {"INFO", "WARNING", "ERROR"}
        error_row = next(r for r in rows if r["severity"] == "ERROR")
        assert error_row["message"] == "boom"
        assert error_row["request_id"] == "r1"
        info_row = next(r for r in rows if r["severity"] == "INFO")
        assert info_row["message"] == "hello"
    finally:
        conn.close()


def test_db_handler_not_duplicated_on_second_configure(
    _isolate_root_handlers: None,
) -> None:
    conn = connect(":memory:")
    init_schema(conn)
    try:
        configure(logging.INFO, db=conn)
        configure(logging.INFO, db=conn)
        logging.getLogger("svc").warning("once")
        rows = select_logs(conn)
        assert len(rows) == 1
    finally:
        conn.close()
