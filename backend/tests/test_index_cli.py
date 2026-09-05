import json
from pathlib import Path

import pytest

from app.config import load_config
from app.index.__main__ import main
from app.index.metadata import IndexMetadata
from tests.conftest import SAMPLE_DOCS

_MULTI_SENTENCE_DOCS = [
    {
        "doc_id": "long-001",
        "title": "Rivers",
        "text": (
            "The river floods in spring. Snowmelt swells the banks. "
            "Farmers watch the levels daily. By summer the flow drops again."
        ),
        "source": "sample",
        "created_at": "2024-02-01T00:00:00Z",
    },
]


def _write_corpus(processed_dir: Path) -> Path:
    path = processed_dir / "docs.jsonl"
    path.write_text(
        "".join(json.dumps(doc) + "\n" for doc in SAMPLE_DOCS),
        encoding="utf-8",
    )
    return path


def _write_docs(processed_dir: Path, docs: list[dict[str, str]]) -> Path:
    path = processed_dir / "docs.jsonl"
    path.write_text(
        "".join(json.dumps(doc) + "\n" for doc in docs),
        encoding="utf-8",
    )
    return path


def test_build_then_second_run_is_up_to_date(
    tmp_repo: Path,
    fake_embedder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = load_config()
    corpus = _write_corpus(settings.processed_dir)

    first = main(["--input", str(corpus)], embedder=fake_embedder)
    assert first == 0
    out = capsys.readouterr().out
    assert "built index:" in out
    assert f"count={len(SAMPLE_DOCS)}" in out
    assert f"dim={fake_embedder.dimension}" in out

    index_dir = settings.index_dir
    assert (index_dir / "metadata.json").is_file()
    assert (index_dir / "bm25" / "bm25.pkl").is_file()
    assert (index_dir / "vector" / "index.faiss").is_file()

    second = main(["--input", str(corpus)], embedder=fake_embedder)
    assert second == 0
    assert "up to date" in capsys.readouterr().out


def test_force_rebuilds_even_when_up_to_date(
    tmp_repo: Path,
    fake_embedder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = load_config()
    corpus = _write_corpus(settings.processed_dir)

    main(["--input", str(corpus)], embedder=fake_embedder)
    capsys.readouterr()

    code = main(["--input", str(corpus), "--force"], embedder=fake_embedder)
    assert code == 0
    assert "built index:" in capsys.readouterr().out


def test_sentence_granularity_makes_more_vectors_than_docs(
    tmp_repo: Path,
    fake_embedder,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A tiny token budget forces one chunk per sentence.
    monkeypatch.setenv("HSS_MAX_SEQ_LENGTH", "4")
    load_config.cache_clear()
    settings = load_config()
    corpus = _write_docs(settings.processed_dir, _MULTI_SENTENCE_DOCS)

    code = main(
        ["--input", str(corpus), "--granularity", "sentence"],
        embedder=fake_embedder,
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "granularity=sentence" in out

    meta = IndexMetadata.load(settings.index_dir)
    assert meta.granularity == "sentence"
    assert meta.doc_count == 1
    assert meta.vector_count > meta.doc_count


def test_switching_granularity_triggers_rebuild(
    tmp_repo: Path,
    fake_embedder,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = load_config()
    corpus = _write_corpus(settings.processed_dir)

    main(["--input", str(corpus), "--granularity", "document"], embedder=fake_embedder)
    capsys.readouterr()

    # Same corpus + model, different granularity -> not up to date, rebuilds.
    code = main(
        ["--input", str(corpus), "--granularity", "sentence"], embedder=fake_embedder
    )
    assert code == 0
    assert "built index:" in capsys.readouterr().out
    assert IndexMetadata.load(settings.index_dir).granularity == "sentence"
