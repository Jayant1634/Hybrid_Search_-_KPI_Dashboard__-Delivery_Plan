from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.config import load_config
from app.eval.__main__ import main
from app.index.metadata import IndexMetadata


@dataclass(frozen=True)
class _Hit:
    doc_id: str


class _Searcher:
    def search(
        self,
        query: str,
        top_k: int = 10,
        alpha: float = 0.5,
        normalization: str = "min_max",
    ) -> list[_Hit]:
        return [_Hit("doc-a")]


class _Service:
    searcher = _Searcher()


def _write_eval_files(eval_dir: Path) -> tuple[Path, Path]:
    queries = eval_dir / "queries.jsonl"
    queries.write_text(
        '{"query_id": "q1", "query": "volcano lava"}\n',
        encoding="utf-8",
    )
    qrels = eval_dir / "qrels.json"
    qrels.write_text('{"q1": {"doc-a": 1}}\n', encoding="utf-8")
    return queries, qrels


def test_eval_cli_writes_a_row(tmp_repo: Path) -> None:
    settings = load_config()
    IndexMetadata.create(
        model="fake-model",
        dimension=8,
        corpus_hash="abc",
        doc_count=1,
    ).save(settings.index_dir)
    queries, qrels = _write_eval_files(settings.eval_dir)

    code = main(
        [
            "--queries",
            "data/eval/queries.jsonl",
            "--qrels",
            "data/eval/qrels.json",
            "--alpha",
            "0.4",
            "--normalization",
            "minmax",
            "--model",
            "fake-model",
            "--preprocessing",
            "none",
            "--tag",
            "baseline",
        ],
        service=_Service(),
    )
    assert code == 0

    csv_path = settings.metrics_dir / "experiments.csv"
    assert csv_path.is_file()
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    row = rows[0]
    assert row["tag"] == "baseline"
    assert row["alpha"] == "0.4"
    assert row["normalization"] == "minmax"
    assert row["model"] == "fake-model"
    assert row["preprocessing"] == "none"
    assert float(row["ndcg10"]) == 1.0
    assert float(row["recall10"]) == 1.0
    assert float(row["mrr10"]) == 1.0
    assert row["n_queries"] == "1"
    assert row["commit"]
    assert row["timestamp"]
    # unused here but kept so the relative default paths are exercised
    assert queries.is_file() and qrels.is_file()


def test_eval_cli_refuses_model_mismatch(
    tmp_repo: Path, capsys
) -> None:
    settings = load_config()
    IndexMetadata.create(
        model="index-model",
        dimension=8,
        corpus_hash="abc",
        doc_count=1,
    ).save(settings.index_dir)
    _write_eval_files(settings.eval_dir)

    code = main(
        ["--model", "other-model", "--tag", "nope"],
        service=_Service(),
    )
    captured = capsys.readouterr()
    assert code == 1
    assert "python -m app.index" in captured.err
    assert "other-model" in captured.err
    assert not (settings.metrics_dir / "experiments.csv").is_file()
