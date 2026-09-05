import json
from pathlib import Path

import pytest

from app.config import load_config
from app.index.__main__ import main
from tests.conftest import SAMPLE_DOCS


def _write_corpus(processed_dir: Path) -> Path:
    path = processed_dir / "docs.jsonl"
    path.write_text(
        "".join(json.dumps(doc) + "\n" for doc in SAMPLE_DOCS),
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
