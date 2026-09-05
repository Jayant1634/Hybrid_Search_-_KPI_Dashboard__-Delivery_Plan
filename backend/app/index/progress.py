"""Process-wide reindex progress, safe to read while a rebuild is running.

``POST /reindex`` writes here from the encode thread; ``GET /reindex/progress``
reads a snapshot so the UI can poll a live percentage.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class ReindexStatus:
    """One snapshot of an in-flight or finished rebuild."""

    running: bool
    granularity: str | None
    done: int
    total: int
    percent: float
    phase: str
    error: str | None = None


_lock = Lock()
_status = ReindexStatus(
    running=False,
    granularity=None,
    done=0,
    total=0,
    percent=0.0,
    phase="idle",
    error=None,
)


def snapshot() -> ReindexStatus:
    """Return the current status without holding the lock afterwards."""
    with _lock:
        return _status


def start(granularity: str) -> None:
    """Mark a rebuild as running at 0% for ``granularity``."""
    try_start(granularity)


def try_start(granularity: str) -> bool:
    """Start a rebuild unless one is already running. Return True if claimed."""
    global _status
    with _lock:
        if _status.running:
            return False
        _status = ReindexStatus(
            running=True,
            granularity=granularity,
            done=0,
            total=0,
            percent=0.0,
            phase="embedding",
            error=None,
        )
        return True


def update(done: int, total: int) -> None:
    """Record how many of ``total`` texts have been encoded."""
    global _status
    safe_total = max(0, int(total))
    safe_done = max(0, min(int(done), safe_total if safe_total else int(done)))
    percent = 100.0 * safe_done / safe_total if safe_total else 0.0
    with _lock:
        _status = ReindexStatus(
            running=True,
            granularity=_status.granularity,
            done=safe_done,
            total=safe_total,
            percent=percent,
            phase="embedding",
            error=None,
        )


def finishing() -> None:
    """Encode is done; FAISS / service reload is still in flight."""
    global _status
    with _lock:
        _status = ReindexStatus(
            running=True,
            granularity=_status.granularity,
            done=_status.total or _status.done,
            total=_status.total,
            percent=100.0 if _status.total else _status.percent,
            phase="finishing",
            error=None,
        )


def finish() -> None:
    """Mark the rebuild complete."""
    global _status
    with _lock:
        _status = ReindexStatus(
            running=False,
            granularity=_status.granularity,
            done=_status.total or _status.done,
            total=_status.total,
            percent=100.0,
            phase="idle",
            error=None,
        )


def fail(message: str | None = None) -> None:
    """Mark the rebuild as no longer running after an error."""
    global _status
    with _lock:
        _status = ReindexStatus(
            running=False,
            granularity=_status.granularity,
            done=_status.done,
            total=_status.total,
            percent=_status.percent,
            phase="idle",
            error=message,
        )
