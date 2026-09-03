"""Shared API dependencies: build info and the loaded search service.

``get_version`` reads the package version from ``pyproject.toml``; ``get_commit``
reports the current git short SHA (falling back to ``HSS_COMMIT`` then
``"unknown"``) and never raises. ``SearchService`` loads the processed corpus and
both indexes exactly once at startup and holds a ready ``HybridSearcher``; if any
piece is missing it raises with the exact command needed to build it.
"""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path

from app.config import Settings, load_config
from app.ingest.writer import Doc, read_jsonl
from app.search.bm25 import BM25Index
from app.search.embedder import Embedder
from app.search.hybrid import HybridSearcher
from app.search.vector import VectorIndex

_BM25_SUBDIR = "bm25"
_VECTOR_SUBDIR = "vector"
_DOCS_FILENAME = "docs.jsonl"
_INGEST_CMD = "python -m app.ingest"
_INDEX_CMD = "python -m app.index"


def _pyproject_path() -> Path:
    # deps.py -> app/api/deps.py, so the backend project root is two up.
    return Path(__file__).resolve().parents[2] / "pyproject.toml"


def get_version() -> str:
    """Return the project version from ``pyproject.toml``."""
    with _pyproject_path().open("rb") as handle:
        data = tomllib.load(handle)
    return str(data["project"]["version"])


def get_commit() -> str:
    """Return the git short SHA, else ``HSS_COMMIT``, else ``"unknown"``.

    Never raises: any git failure or missing binary falls through to the
    environment override and finally the literal ``"unknown"``.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).resolve().parent,
        )
        commit = result.stdout.strip()
        if commit:
            return commit
    except Exception:
        pass
    env_commit = os.environ.get("HSS_COMMIT", "").strip()
    if env_commit:
        return env_commit
    return "unknown"


class SearchService:
    """Holds the loaded corpus, indexes, and a ready ``HybridSearcher``."""

    def __init__(
        self, searcher: HybridSearcher, docs_by_id: dict[str, dict[str, str]]
    ) -> None:
        self.searcher = searcher
        self.docs_by_id = docs_by_id

    @classmethod
    def load(
        cls,
        embedder: Embedder,
        settings: Settings | None = None,
    ) -> SearchService:
        """Load the corpus and both indexes once, or raise a build hint.

        ``embedder`` must match the one used to build the vector index. A
        missing corpus or index raises ``RuntimeError`` naming the command that
        produces it.
        """
        settings = settings or load_config()

        docs_path = settings.processed_dir / _DOCS_FILENAME
        if not docs_path.is_file():
            raise RuntimeError(
                f"corpus not found at {docs_path}; build it with: {_INGEST_CMD}"
            )

        bm25_dir = settings.index_dir / _BM25_SUBDIR
        vector_dir = settings.index_dir / _VECTOR_SUBDIR
        if not (bm25_dir / "bm25.pkl").is_file():
            raise RuntimeError(
                f"BM25 index not found in {bm25_dir}; build it with: {_INDEX_CMD}"
            )
        if not (vector_dir / "index.faiss").is_file():
            raise RuntimeError(
                f"vector index not found in {vector_dir}; "
                f"build it with: {_INDEX_CMD}"
            )

        docs: list[Doc] = read_jsonl(docs_path)
        docs_by_id: dict[str, dict[str, str]] = {
            doc.doc_id: {
                "doc_id": doc.doc_id,
                "title": doc.title,
                "text": doc.text,
                "source": doc.source,
                "created_at": doc.created_at,
            }
            for doc in docs
        }

        bm25 = BM25Index.load(bm25_dir)
        vector = VectorIndex.load(vector_dir)
        searcher = HybridSearcher(bm25, vector, embedder, docs_by_id)
        return cls(searcher, docs_by_id)
