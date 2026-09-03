from pathlib import Path

import pytest

from app.config import load_config
from app.ingest import ingest, main
from app.ingest.writer import read_jsonl


def _long_body(seed: str = "A volcano is a mountain that erupts lava and ash. ") -> str:
    return seed * 8


def test_cli_writes_two_skips_short(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw = tmp_path / "raw"
    out = tmp_path / "processed"
    raw.mkdir()
    (raw / "volcano.md").write_text(
        "---\n"
        'title: "Volcano"\n'
        'source: "https://simple.wikipedia.org/wiki/Volcano"\n'
        'fetched: "2026-09-03"\n'
        "---\n"
        "\n"
        f"{_long_body()}\n",
        encoding="utf-8",
    )
    (raw / "mars.txt").write_text(
        "Mars is the red planet. " * 12,
        encoding="utf-8",
    )
    (raw / "short.md").write_text("too short\n", encoding="utf-8")

    monkeypatch.setenv("HSS_REPO_ROOT", str(tmp_path))
    load_config.cache_clear()
    try:
        code = main(["--input", str(raw), "--out", str(out)])
    finally:
        load_config.cache_clear()

    assert code == 0
    docs = read_jsonl(out / "docs.jsonl")
    assert len(docs) == 2
    titles = {doc.title for doc in docs}
    assert titles == {"Volcano", "mars"}
    assert (out / "manifest.json").is_file()
    captured = capsys.readouterr()
    assert "skipped: short.md (too short" in captured.out
    assert "wrote 2, skipped 1" in captured.out


def test_cli_exit_1_when_nothing_written(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = tmp_path / "raw"
    out = tmp_path / "processed"
    raw.mkdir()
    (raw / "short.md").write_text("nope\n", encoding="utf-8")
    monkeypatch.setenv("HSS_REPO_ROOT", str(tmp_path))
    load_config.cache_clear()
    try:
        code = main(["--input", str(raw), "--out", str(out)])
    finally:
        load_config.cache_clear()
    assert code == 1
    assert not (out / "docs.jsonl").exists()


def test_sentence_split_flag(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    out = tmp_path / "processed"
    raw.mkdir()
    body = (
        "Lava is hot. Ash can travel far. Rocks cool slowly. "
        "Magma comes from deep in the Earth. "
    ) * 5
    (raw / "volcano.md").write_text(body, encoding="utf-8")
    path = ingest(raw, out, sentence_split=True)
    assert path is not None
    doc = read_jsonl(path)[0]
    lines = doc.text.splitlines()
    assert len(lines) >= 2
    assert all(line for line in lines)
