"""Shared fake docs and tmp-repo fixtures."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.config import load_config

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
