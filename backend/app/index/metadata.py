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
    granularity: str = "document"
    vector_count: int = 0

    @classmethod
    def create(
        cls,
        model: str,
        dimension: int,
        corpus_hash: str,
        doc_count: int,
        built_at: str | None = None,
        granularity: str = "document",
        vector_count: int | None = None,
    ) -> IndexMetadata:
        """Build metadata, defaulting ``built_at`` to the current UTC time.

        ``vector_count`` defaults to ``doc_count`` (document granularity: one
        vector per doc); sentence granularity passes the real chunk count.
        """
        if built_at is None:
            built_at = datetime.now(timezone.utc).isoformat()
        if vector_count is None:
            vector_count = doc_count
        return cls(
            model=model,
            dimension=int(dimension),
            corpus_hash=corpus_hash,
            doc_count=int(doc_count),
            built_at=built_at,
            granularity=granularity,
            vector_count=int(vector_count),
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
        doc_count = int(payload["doc_count"])
        return cls(
            model=payload["model"],
            dimension=int(payload["dimension"]),
            corpus_hash=payload["corpus_hash"],
            doc_count=doc_count,
            built_at=payload["built_at"],
            granularity=payload.get("granularity", "document"),
            vector_count=int(payload.get("vector_count", doc_count)),
        )


def is_up_to_date(
    folder: Path | str,
    corpus_hash: str,
    model: str,
    granularity: str | None = None,
) -> bool:
    """Return ``True`` only if a saved index matches the given build inputs.

    An index is stale when no metadata file exists, the corpus hash differs, the
    embedding model differs, or (when ``granularity`` is given) the saved
    granularity differs. Switching between document and sentence indexing
    therefore forces a rebuild.
    """
    path = Path(folder) / _METADATA_FILE
    if not path.is_file():
        return False
    try:
        meta = IndexMetadata.load(folder)
    except (json.JSONDecodeError, KeyError):
        return False
    if meta.corpus_hash != corpus_hash or meta.model != model:
        return False
    if granularity is not None and meta.granularity != granularity:
        return False
    return True
