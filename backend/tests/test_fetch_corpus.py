from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path
from typing import Any

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import fetch_corpus  # noqa: E402


LONG_TEXT = "A volcano is a mountain that erupts lava. " * 20


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _page_payload(
    title: str,
    extract: str,
    *,
    missing: bool = False,
    fullurl: str | None = None,
    redirects: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    page: dict[str, Any] = {"title": title}
    if missing:
        page["missing"] = True
    else:
        page["extract"] = extract
        page["fullurl"] = fullurl or f"https://simple.wikipedia.org/wiki/{title.replace(' ', '_')}"
    query: dict[str, Any] = {"pages": [page]}
    if redirects:
        query["redirects"] = redirects
    return {"query": query}


def _write_seed(root: Path, rows: list[tuple[str, str]]) -> None:
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    lines = "".join(f"{topic}\t{title}\n" for topic, title in rows)
    (raw / "seed_titles.txt").write_text(lines, encoding="utf-8")


def test_repo_root_follows_script_not_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    expected = Path(fetch_corpus.__file__).resolve().parent.parent
    assert fetch_corpus.repo_root() == expected


def test_slugify_and_article_slug() -> None:
    assert fetch_corpus.slugify("Mercury (planet)") == "mercury-planet"
    assert fetch_corpus.slugify("Hadrian's Wall") == "hadrian-s-wall"
    assert fetch_corpus.article_slug("inventions", "Airplane") == "inventions-airplane"
    assert fetch_corpus.article_slug("transport", "Airplane") == "transport-airplane"


def test_read_seed_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "seed_titles.txt"
    path.write_text("volcanoes\tVolcano\n\nplanets\tMars\n", encoding="utf-8")
    rows = fetch_corpus.read_seed(path)
    assert [(row.topic, row.title) for row in rows] == [
        ("volcanoes", "Volcano"),
        ("planets", "Mars"),
    ]


def test_writes_front_matter_and_follows_redirect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_seed(tmp_path, [("planets", "USA")])
    monkeypatch.setattr(fetch_corpus, "today_iso", lambda: "2026-09-03")
    monkeypatch.setattr(fetch_corpus.time, "sleep", lambda _s: None)

    def fake_urlopen(request: object, timeout: int = 30) -> FakeResponse:
        url = request.full_url  # type: ignore[attr-defined]
        assert "redirects=1" in url
        assert "explaintext=1" in url
        assert "titles=USA" in url
        return FakeResponse(
            _page_payload(
                "United States",
                LONG_TEXT,
                fullurl="https://simple.wikipedia.org/wiki/United_States",
                redirects=[{"from": "USA", "to": "United States"}],
            )
        )

    monkeypatch.setattr(fetch_corpus.urllib.request, "urlopen", fake_urlopen)
    assert fetch_corpus.main([], root=tmp_path) == 0
    out = tmp_path / "data" / "raw" / "planets-usa.md"
    text = out.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert 'title: "United States"' in text
    assert 'source: "https://simple.wikipedia.org/wiki/United_States"' in text
    assert 'license: "CC BY-SA 4.0"' in text
    assert 'topic: "planets"' in text
    assert 'fetched: "2026-09-03"' in text
    assert LONG_TEXT.strip() in text
    captured = capsys.readouterr()
    assert "wrote 1, skipped 0" in captured.out
    attribution = (tmp_path / "data" / "raw" / "ATTRIBUTION.md").read_text(encoding="utf-8")
    lines = attribution.splitlines()
    assert lines[0] == (
        "These articles come from Simple English Wikipedia and are licensed under CC BY-SA 4.0."
    )
    assert lines[1] == (
        "See the license at https://creativecommons.org/licenses/by-sa/4.0/ "
        "for how to credit authors and share adaptations."
    )
    assert lines[2] == ""
    assert lines[3] == "United States https://simple.wikipedia.org/wiki/United_States"


def test_skips_short_extract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_seed(tmp_path, [("volcanoes", "Magma")])
    monkeypatch.setattr(fetch_corpus.time, "sleep", lambda _s: None)
    monkeypatch.setattr(
        fetch_corpus.urllib.request,
        "urlopen",
        lambda request, timeout=30: FakeResponse(_page_payload("Magma", "too short")),
    )
    assert fetch_corpus.main([], root=tmp_path) == 0
    raw = tmp_path / "data" / "raw"
    assert [p.name for p in raw.glob("*.md")] == ["ATTRIBUTION.md"]
    attribution = (raw / "ATTRIBUTION.md").read_text(encoding="utf-8")
    assert "https://creativecommons.org/licenses/by-sa/4.0/" in attribution
    assert "Magma" not in attribution
    captured = capsys.readouterr()
    assert "skipped: Magma" in captured.out
    assert "extract 9 chars, need 400" in captured.out
    assert "wrote 0, skipped 1" in captured.out


def test_limit_fetches_only_n(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_seed(
        tmp_path,
        [("volcanoes", "Volcano"), ("volcanoes", "Lava"), ("volcanoes", "Magma")],
    )
    seen: list[str] = []

    def fake_urlopen(request: object, timeout: int = 30) -> FakeResponse:
        url = request.full_url  # type: ignore[attr-defined]
        title = url.rsplit("titles=", 1)[-1]
        seen.append(title)
        return FakeResponse(_page_payload(title, LONG_TEXT))

    monkeypatch.setattr(fetch_corpus.time, "sleep", lambda _s: None)
    monkeypatch.setattr(fetch_corpus.urllib.request, "urlopen", fake_urlopen)
    assert fetch_corpus.main(["--limit", "2"], root=tmp_path) == 0
    assert seen == ["Volcano", "Lava"]
    md_files = sorted(p.name for p in (tmp_path / "data" / "raw").glob("*.md"))
    assert md_files == ["ATTRIBUTION.md", "volcanoes-lava.md", "volcanoes-volcano.md"]
    attribution = (tmp_path / "data" / "raw" / "ATTRIBUTION.md").read_text(encoding="utf-8")
    assert "Volcano https://simple.wikipedia.org/wiki/Volcano" in attribution
    assert "Lava https://simple.wikipedia.org/wiki/Lava" in attribution
    assert "Magma" not in attribution


def test_retries_three_times_then_skips(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_seed(tmp_path, [("stars", "Sun")])
    calls = {"n": 0}
    sleeps: list[float] = []

    def fake_urlopen(request: object, timeout: int = 30) -> FakeResponse:
        calls["n"] += 1
        raise urllib.error.URLError("temporary")

    monkeypatch.setattr(fetch_corpus.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(fetch_corpus.urllib.request, "urlopen", fake_urlopen)
    assert fetch_corpus.main([], root=tmp_path) == 0
    assert calls["n"] == 3
    assert sleeps == [0.5, 0.5]
    raw = tmp_path / "data" / "raw"
    assert [p.name for p in raw.glob("*.md")] == ["ATTRIBUTION.md"]
    assert "Sun" not in (raw / "ATTRIBUTION.md").read_text(encoding="utf-8")
    captured = capsys.readouterr()
    assert "skipped: Sun (failed after 3 tries:" in captured.out


def test_keeps_extract_of_exactly_400_chars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_seed(tmp_path, [("oceans", "Ocean")])
    monkeypatch.setattr(fetch_corpus.time, "sleep", lambda _s: None)
    monkeypatch.setattr(
        fetch_corpus.urllib.request,
        "urlopen",
        lambda request, timeout=30: FakeResponse(_page_payload("Ocean", "x" * 400)),
    )
    assert fetch_corpus.main([], root=tmp_path) == 0
    assert (tmp_path / "data" / "raw" / "oceans-ocean.md").is_file()
    attribution = (tmp_path / "data" / "raw" / "ATTRIBUTION.md").read_text(encoding="utf-8")
    assert "Ocean https://simple.wikipedia.org/wiki/Ocean" in attribution
