from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import fetch_corpus  # noqa: E402
import fetch_until_done  # noqa: E402

LONG_TEXT = "A volcano is a mountain that erupts lava. " * 20


def _write_seed(root: Path, rows: list[tuple[str, str]]) -> None:
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    lines = "".join(f"{topic}\t{title}\n" for topic, title in rows)
    (raw / "seed_titles.txt").write_text(lines, encoding="utf-8")


def test_until_done_loops_until_all_extracted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_seed(
        tmp_path,
        [("volcanoes", "Volcano"), ("volcanoes", "Lava"), ("volcanoes", "Magma")],
    )
    calls = {"n": 0}

    def fake_main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
        assert root is not None
        calls["n"] += 1
        raw = root / "data" / "raw"
        seed = fetch_corpus.read_seed(raw / "seed_titles.txt")
        pending = fetch_corpus.pending_rows(raw, seed)
        row = pending[0]
        fetch_corpus.article_path(raw, row).write_text(
            fetch_corpus.render_markdown(
                title=row.title,
                source=f"https://simple.wikipedia.org/wiki/{row.title}",
                topic=row.topic,
                fetched="2026-09-03",
                body=LONG_TEXT,
            ),
            encoding="utf-8",
        )
        fetch_corpus.write_attribution(raw)
        return 0

    monkeypatch.setattr(fetch_until_done.fetch_corpus, "main", fake_main)
    assert fetch_until_done.main(["--wait", "0"], root=tmp_path) == 0
    assert calls["n"] == 3
    raw = tmp_path / "data" / "raw"
    names = sorted(p.name for p in raw.glob("volcanoes-*.md"))
    assert names == ["volcanoes-lava.md", "volcanoes-magma.md", "volcanoes-volcano.md"]


def test_until_done_stops_when_nothing_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_seed(tmp_path, [("oceans", "Ocean")])
    raw = tmp_path / "data" / "raw"
    (raw / "oceans-ocean.md").write_text(
        fetch_corpus.render_markdown(
            title="Ocean",
            source="https://simple.wikipedia.org/wiki/Ocean",
            topic="oceans",
            fetched="2026-09-03",
            body=LONG_TEXT,
        ),
        encoding="utf-8",
    )
    calls = {"n": 0}

    def fake_main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
        calls["n"] += 1
        return 0

    monkeypatch.setattr(fetch_until_done.fetch_corpus, "main", fake_main)
    assert fetch_until_done.main(["--wait", "0"], root=tmp_path) == 0
    assert calls["n"] == 0
    assert (raw / "ATTRIBUTION.md").is_file()
