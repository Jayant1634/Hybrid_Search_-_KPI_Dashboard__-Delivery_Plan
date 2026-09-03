from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.eval.runner import (
    EvalResult,
    Query,
    append_experiment,
    load_qrels,
    load_queries,
    run_eval,
)


@dataclass(frozen=True)
class _Hit:
    doc_id: str


class _Searcher:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def search(
        self,
        query: str,
        top_k: int = 10,
        alpha: float = 0.5,
        normalization: str = "min_max",
    ) -> list[_Hit]:
        self.calls.append(
            {
                "query": query,
                "top_k": top_k,
                "alpha": alpha,
                "normalization": normalization,
            }
        )
        ranking = {
            "volcano lava": ["doc-a", "doc-x"],
            "python scripts": ["doc-x", "doc-b"],
        }
        return [_Hit(doc_id) for doc_id in ranking.get(query, [])]


class _Service:
    def __init__(self) -> None:
        self.searcher = _Searcher()


_QUERIES = [
    Query("q1", "volcano lava"),
    Query("q2", "python scripts"),
    Query("q3", "no labels"),
]
_QRELS = {
    "q1": {"doc-a": 1.0},
    "q2": {"doc-b": 1.0, "doc-c": 1.0},
}


def test_load_queries_and_qrels(tmp_path: Path) -> None:
    queries_path = tmp_path / "queries.jsonl"
    queries_path.write_text(
        '{"query_id": "q1", "query": "volcano lava"}\n\n'
        '{"query_id": "q2", "query": "python scripts"}\n',
        encoding="utf-8",
    )
    qrels_path = tmp_path / "qrels.json"
    qrels_path.write_text(
        '{"q1": {"doc-a": 1}, "q2": {"doc-b": 1, "doc-c": 1}}\n',
        encoding="utf-8",
    )
    assert load_queries(queries_path) == [
        Query("q1", "volcano lava"),
        Query("q2", "python scripts"),
    ]
    assert load_qrels(qrels_path) == _QRELS


def test_run_eval_means_and_per_query() -> None:
    service = _Service()
    result = run_eval(service, _QUERIES[:2], _QRELS, 0.3, "z_score")

    # q1: ranked [doc-a, doc-x], relevant {doc-a:1}
    #   nDCG = 1.0, Recall = 1.0, MRR = 1.0
    # q2: ranked [doc-x, doc-b], relevant {doc-b:1, doc-c:1}
    #   DCG  = 0/log2(2) + 1/log2(3) = 1/log2(3)
    #   IDCG = 1/log2(2) + 1/log2(3) = 1 + 1/log2(3)
    #   nDCG = (1/log2(3)) / (1 + 1/log2(3))
    #   Recall = 1/2, MRR = 1/2
    q2_ndcg = (1.0 / math.log2(3)) / (1.0 + 1.0 / math.log2(3))
    assert result.per_query[0].query_id == "q1"
    assert result.per_query[0].ndcg_at_10 == pytest.approx(1.0)
    assert result.per_query[0].recall_at_10 == pytest.approx(1.0)
    assert result.per_query[0].mrr_at_10 == pytest.approx(1.0)
    assert result.per_query[1].query_id == "q2"
    assert result.per_query[1].ndcg_at_10 == pytest.approx(q2_ndcg)
    assert result.per_query[1].recall_at_10 == pytest.approx(0.5)
    assert result.per_query[1].mrr_at_10 == pytest.approx(0.5)
    assert result.ndcg_at_10 == pytest.approx((1.0 + q2_ndcg) / 2)
    assert result.recall_at_10 == pytest.approx(0.75)
    assert result.mrr_at_10 == pytest.approx(0.75)
    assert service.searcher.calls == [
        {
            "query": "volcano lava",
            "top_k": 10,
            "alpha": 0.3,
            "normalization": "z_score",
        },
        {
            "query": "python scripts",
            "top_k": 10,
            "alpha": 0.3,
            "normalization": "z_score",
        },
    ]


def test_run_eval_warns_and_skips_missing_qrels() -> None:
    service = _Service()
    with pytest.warns(UserWarning, match="skipping query 'q3': no qrels"):
        result = run_eval(service, _QUERIES, _QRELS, 0.5, "min_max")
    assert [row.query_id for row in result.per_query] == ["q1", "q2"]
    assert all(call["query"] != "no labels" for call in service.searcher.calls)


def test_append_experiment_writes_header_once(tmp_path: Path) -> None:
    path = tmp_path / "metrics" / "experiments.csv"
    row1 = {
        "timestamp": "2026-09-03T00:00:00Z",
        "commit": "abc1234",
        "alpha": 0.5,
        "embedding_model": "fake",
        "preprocessing": "none",
        "ndcg_at_10": 1.0,
        "recall_at_10": 1.0,
        "mrr_at_10": 1.0,
    }
    row2 = {**row1, "alpha": 0.7, "ndcg_at_10": 0.5}
    append_experiment(path, row1)
    append_experiment(path, row2)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == (
        "timestamp,commit,alpha,embedding_model,preprocessing,"
        "ndcg_at_10,recall_at_10,mrr_at_10"
    )
    assert len(lines) == 3
    assert lines[1].startswith("2026-09-03T00:00:00Z,abc1234,0.5,")
    assert ",0.7," in lines[2]


def test_run_eval_empty_after_skips_is_zero() -> None:
    service = _Service()
    with pytest.warns(UserWarning, match="no qrels"):
        result = run_eval(service, [Query("q9", "ghost")], {}, 0.5, "min_max")
    assert result == EvalResult(
        ndcg_at_10=0.0,
        recall_at_10=0.0,
        mrr_at_10=0.0,
        per_query=(),
    )
