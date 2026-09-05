"""Shared fake docs, embedder, and tmp-repo fixtures."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from app.config import load_config


class FakeEmbedder:
    """Deterministic Embedder: hash each text to seed a unit vector of dim 8."""

    dimension = 8

    def encode(
        self,
        texts: list[str],
        on_progress: object | None = None,
    ) -> NDArray[np.float32]:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        rows = np.stack([self._vector(text) for text in texts])
        if on_progress is not None:
            on_progress(len(texts), len(texts))  # type: ignore[operator]
        return np.asarray(rows, dtype=np.float32)

    def _vector(self, text: str) -> NDArray[np.float64]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "little")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self.dimension)
        norm = float(np.linalg.norm(vec))
        if norm == 0.0:
            vec = np.zeros(self.dimension, dtype=np.float64)
            vec[0] = 1.0
        else:
            vec = vec / norm
        return vec

SAMPLE_DOCS: list[dict[str, str]] = [
    {
        "doc_id": "doc-001",
        "title": "Volcanoes",
        "text": "A volcano erupts when magma reaches the surface as lava and ash.",
        "source": "sample",
        "created_at": "2024-01-15T00:00:00Z",
    },
    {
        "doc_id": "doc-002",
        "title": "Bread",
        "text": "Bread is made by baking dough of flour, water, and yeast until the crust browns.",
        "source": "sample",
        "created_at": "2024-01-16T00:00:00Z",
    },
    {
        "doc_id": "doc-003",
        "title": "Python",
        "text": "Python is a programming language used for scripts, APIs, and data work.",
        "source": "sample",
        "created_at": "2024-01-17T00:00:00Z",
    },
    {
        "doc_id": "doc-004",
        "title": "The Moon",
        "text": "The Moon orbits Earth and lights the night sky with reflected sunlight.",
        "source": "sample",
        "created_at": "2024-01-18T00:00:00Z",
    },
    {
        "doc_id": "doc-005",
        "title": "Football",
        "text": "Football is a team sport where players score by kicking a ball into the goal.",
        "source": "sample",
        "created_at": "2024-01-19T00:00:00Z",
    },
    {
        "doc_id": "doc-006",
        "title": "Jazz",
        "text": "Jazz is a music style built on swing rhythm, improvisation, and blue notes.",
        "source": "sample",
        "created_at": "2024-01-20T00:00:00Z",
    },
]

_DATA_FOLDERS = ("raw", "processed", "index", "eval", "metrics")


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def sample_docs() -> list[dict[str, str]]:
    return list(SAMPLE_DOCS)


@pytest.fixture
def sample_docs_jsonl(tmp_path: Path) -> Path:
    path = tmp_path / "docs.jsonl"
    path.write_text(
        "".join(json.dumps(doc) + "\n" for doc in SAMPLE_DOCS),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def tmp_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    data_dir = tmp_path / "data"
    for name in _DATA_FOLDERS:
        (data_dir / name).mkdir(parents=True)
    monkeypatch.setenv("HSS_REPO_ROOT", str(tmp_path))
    load_config.cache_clear()
    yield tmp_path
    load_config.cache_clear()
