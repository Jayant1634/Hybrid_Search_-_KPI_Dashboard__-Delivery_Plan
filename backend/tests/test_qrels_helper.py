from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import qrels_helper  # noqa: E402


@dataclass(frozen=True)
class _Hit:
    doc_id: str
    title: str


class _Searcher:
    def search(self, query: str, top_k: int = 20) -> list[_Hit]:
        assert top_k == 20
        if query == "volcano lava":
            return [_Hit("doc-001", "Volcanoes"), _Hit("doc-004", "The Moon")][:top_k]
        return [_Hit("doc-003", "Python")][:top_k]


class _Service:
    searcher = _Searcher()


def test_read_queries_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "queries.txt"
    path.write_text("volcano lava\n\n  \npython scripts\n", encoding="utf-8")
    assert qrels_helper.read_queries(path) == ["volcano lava", "python scripts"]


def test_label_queries_prints_ids_and_titles() -> None:
    text = qrels_helper.label_queries(_Service(), ["volcano lava", "python"])
    assert text.startswith("=== volcano lava ===")
    assert "1. doc-001\tVolcanoes" in text
    assert "2. doc-004\tThe Moon" in text
    assert "=== python ===" in text
    assert "1. doc-003\tPython" in text
    assert qrels_helper.TOP_K == 20


def test_main_missing_file_is_one(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "nope.txt"
    code = qrels_helper.main([str(missing)])
    captured = capsys.readouterr()
    assert code == 1
    assert "queries file not found" in captured.err
