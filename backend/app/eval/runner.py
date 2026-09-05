"""Load eval queries/qrels, score a service, and append experiment rows.

``run_eval`` searches each query, scores nDCG@10 / Recall@10 / MRR@10, and
returns the means plus the per-query numbers. Queries with no qrels are
warned about and skipped. ``append_experiment`` writes the CSV header only
when the file is new or empty.
"""

from __future__ import annotations

import csv
import json
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.eval.metrics import DEFAULT_K, mrr_at_k, ndcg_at_k, recall_at_k


class Hit(Protocol):
    doc_id: str


class Searcher(Protocol):
    def search(
        self,
        query: str,
        top_k: int = DEFAULT_K,
        alpha: float = 0.5,
        normalization: str = "min_max",
    ) -> Sequence[Hit]: ...


class Service(Protocol):
    searcher: Searcher


@dataclass(frozen=True)
class Query:
    query_id: str
    query: str


@dataclass(frozen=True)
class QueryScores:
    query_id: str
    ndcg_at_10: float
    recall_at_10: float
    mrr_at_10: float


@dataclass(frozen=True)
class EvalResult:
    ndcg_at_10: float
    recall_at_10: float
    mrr_at_10: float
    per_query: tuple[QueryScores, ...]


def load_queries(path: Path) -> list[Query]:
    """Read ``query_id`` / ``query`` objects from a JSONL file."""
    queries: list[Query] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        obj = json.loads(line)
        queries.append(Query(query_id=str(obj["query_id"]), query=str(obj["query"])))
    return queries


def load_qrels(path: Path) -> dict[str, dict[str, float]]:
    """Read ``query_id -> {doc_id: gain}`` from a JSON object."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(query_id): {str(doc_id): float(gain) for doc_id, gain in docs.items()}
        for query_id, docs in payload.items()
    }


def _as_query(item: Query | Mapping[str, str]) -> Query:
    if isinstance(item, Query):
        return item
    return Query(query_id=str(item["query_id"]), query=str(item["query"]))


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def run_eval(
    service: Service,
    queries: Sequence[Query | Mapping[str, str]],
    qrels: Mapping[str, Mapping[str, float]],
    alpha: float,
    normalization: str,
    rrf_k: int | None = None,
) -> EvalResult:
    """Score ``queries`` with ``service``; skip any query that has no qrels."""
    per_query: list[QueryScores] = []
    for item in queries:
        query = _as_query(item)
        relevant = qrels.get(query.query_id)
        if not relevant:
            warnings.warn(
                f"skipping query {query.query_id!r}: no qrels",
                UserWarning,
                stacklevel=2,
            )
            continue
        if rrf_k is None:
            hits = service.searcher.search(
                query.query,
                top_k=DEFAULT_K,
                alpha=alpha,
                normalization=normalization,
            )
        else:
            hits = service.searcher.search(
                query.query,
                top_k=DEFAULT_K,
                alpha=alpha,
                normalization=normalization,
                rrf_k=rrf_k,
            )
        ranked = [hit.doc_id for hit in hits]
        per_query.append(
            QueryScores(
                query_id=query.query_id,
                ndcg_at_10=ndcg_at_k(ranked, relevant),
                recall_at_10=recall_at_k(ranked, relevant),
                mrr_at_10=mrr_at_k(ranked, relevant),
            )
        )
    return EvalResult(
        ndcg_at_10=_mean([row.ndcg_at_10 for row in per_query]),
        recall_at_10=_mean([row.recall_at_10 for row in per_query]),
        mrr_at_10=_mean([row.mrr_at_10 for row in per_query]),
        per_query=tuple(per_query),
    )


def append_experiment(csv_path: Path, row: Mapping[str, object]) -> None:
    """Append ``row`` to ``csv_path``, writing the header only once."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.is_file() or csv_path.stat().st_size == 0
    if write_header:
        fieldnames = list(row.keys())
    else:
        with csv_path.open(encoding="utf-8", newline="") as handle:
            existing = next(csv.reader(handle), [])
        fieldnames = existing or list(row.keys())
    with csv_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(dict(row))
