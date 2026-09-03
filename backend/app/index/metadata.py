"""Sidecar metadata describing a built index, with staleness checks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

_METADATA_FILE = "metadata.json"


@dataclass(frozen=True)
class IndexMetadata:
    """Describes how and when an index was built."""

    model: str
    dimension: int
    corpus_hash: str
    doc_count: int
    built_at: str

    @classmethod
    def create(
        cls,
        model: str,
        dimension: int,
        corpus_hash: str,
        doc_count: int,
        built_at: str | None = None,
    ) -> IndexMetadata:
        """Build metadata, defaulting ``built_at`` to the current UTC time."""
        if built_at is None:
            built_at = datetime.now(timezone.utc).isoformat()
        return cls(
            model=model,
            dimension=int(dimension),
            corpus_hash=corpus_hash,
            doc_count=int(doc_count),
            built_at=built_at,
        )

    def save(self, folder: Path | str) -> Path:
        """Write ``metadata.json`` into ``folder`` and return its path."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / _METADATA_FILE
        path.write_text(
            json.dumps(asdict(self), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    @classmethod
    def load(cls, folder: Path | str) -> IndexMetadata:
        """Load metadata previously written by :meth:`save`."""
        path = Path(folder) / _METADATA_FILE
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            model=payload["model"],
            dimension=int(payload["dimension"]),
            corpus_hash=payload["corpus_hash"],
            doc_count=int(payload["doc_count"]),
            built_at=payload["built_at"],
        )


def is_up_to_date(folder: Path | str, corpus_hash: str, model: str) -> bool:
    """Return ``True`` only if a saved index matches ``corpus_hash`` and ``model``.

    An index is stale in three ways: no metadata file exists, the corpus hash
    differs, or the embedding model differs.
    """
    path = Path(folder) / _METADATA_FILE
    if not path.is_file():
        return False
    try:
        meta = IndexMetadata.load(folder)
    except (json.JSONDecodeError, KeyError):
        return False
    return meta.corpus_hash == corpus_hash and meta.model == model
