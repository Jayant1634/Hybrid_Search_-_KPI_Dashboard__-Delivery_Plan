"""Eval CLI. Run from the repo root: ``python -m app.eval``.

Scores the loaded index against queries + qrels and appends one row to
``data/metrics/experiments.csv``. ``--model`` must match the index metadata
or the run is refused with the rebuild command.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.config import load_config
from app.eval.runner import Service, append_experiment, load_qrels, load_queries, run_eval
from app.index.metadata import IndexMetadata

_INDEX_CMD = "python -m app.index --force"
_CSV_NAME = "experiments.csv"
_NORMALIZATION = {
    "minmax": "min_max",
    "min_max": "min_max",
    "zscore": "z_score",
    "z_score": "z_score",
    "rrf": "rrf",
}


def _resolve_path(value: str | Path, *, repo_root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).resolve().parent,
        )
        commit = result.stdout.strip()
        if commit:
            return commit
    except Exception:
        pass
    return os.environ.get("HSS_COMMIT", "").strip() or "unknown"


def _search_normalization(name: str) -> str:
    try:
        return _NORMALIZATION[name]
    except KeyError:
        known = ", ".join(sorted(_NORMALIZATION))
        raise ValueError(f"unknown normalization {name!r}; expected one of: {known}") from None


def check_model(index_dir: Path, model: str) -> str | None:
    """Return a refusal message if ``model`` does not match the index."""
    try:
        meta = IndexMetadata.load(index_dir)
    except (OSError, KeyError, ValueError):
        return f"index metadata not found; rebuild with: {_INDEX_CMD}"
    if meta.model != model:
        return (
            f"refusing: --model {model!r} does not match index model "
            f"{meta.model!r}. rebuild with: {_INDEX_CMD}"
        )
    return None


def _build_parser(settings_queries: Path, settings_qrels: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score queries against qrels and append experiments.csv."
    )
    parser.add_argument(
        "--queries",
        type=Path,
        default=settings_queries,
        help="queries JSONL (default: data/eval/queries.jsonl)",
    )
    parser.add_argument(
        "--qrels",
        type=Path,
        default=settings_qrels,
        help="qrels JSON (default: data/eval/qrels.json)",
    )
    parser.add_argument("--alpha", type=float, default=None, help="hybrid blend weight")
    parser.add_argument(
        "--normalization",
        default=None,
        help="minmax, zscore, or rrf (also accepts min_max / z_score)",
    )
    parser.add_argument(
        "--rrf-k",
        type=int,
        default=None,
        help="RRF rank-smoothing k in 1/(k+rank); required when --normalization is rrf",
    )
    parser.add_argument("--model", default=None, help="embedding model; must match the index")
    parser.add_argument(
        "--preprocessing",
        default="",
        help="label only, stored on the experiment row",
    )
    parser.add_argument("--tag", default="", help="label for this run")
    return parser


def main(argv: list[str] | None = None, *, service: Service | None = None) -> int:
    """CLI entry. ``service`` is for tests; the CLI loads ``SearchService``."""
    settings = load_config()
    parser = _build_parser(
        settings.eval_dir / "queries.jsonl",
        settings.eval_dir / "qrels.json",
    )
    args = parser.parse_args(argv)

    alpha = settings.default_alpha if args.alpha is None else float(args.alpha)
    normalization = (
        settings.normalisation if args.normalization is None else str(args.normalization)
    )
    model = settings.embedding_model if args.model is None else str(args.model)

    refusal = check_model(settings.index_dir, model)
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return 1

    try:
        search_norm = _search_normalization(normalization)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    rrf_k = args.rrf_k
    if search_norm == "rrf":
        if rrf_k is None:
            print("rrf requires --rrf-k (rank-smoothing k in 1/(k+rank))", file=sys.stderr)
            return 1
        if rrf_k < 0:
            print("--rrf-k must be >= 0", file=sys.stderr)
            return 1

    queries_path = _resolve_path(args.queries, repo_root=settings.repo_root)
    qrels_path = _resolve_path(args.qrels, repo_root=settings.repo_root)
    queries = load_queries(queries_path)
    qrels = load_qrels(qrels_path)

    if service is None:
        from app.api.deps import SearchService
        from app.search.embedder import SentenceTransformerEmbedder

        service = SearchService.load(SentenceTransformerEmbedder())

    result = run_eval(service, queries, qrels, alpha, search_norm, rrf_k=rrf_k)
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commit": _commit(),
        "tag": args.tag,
        "alpha": alpha,
        "normalization": normalization,
        "model": model,
        "preprocessing": args.preprocessing,
        "ndcg10": result.ndcg_at_10,
        "recall10": result.recall_at_10,
        "mrr10": result.mrr_at_10,
        "n_queries": len(result.per_query),
    }
    csv_path = settings.metrics_dir / _CSV_NAME
    append_experiment(csv_path, row)
    relative = csv_path.relative_to(settings.repo_root).as_posix()
    print(
        f"eval: n={row['n_queries']} ndcg10={result.ndcg_at_10:.4f} "
        f"recall10={result.recall_at_10:.4f} mrr10={result.mrr_at_10:.4f} "
        f"-> {relative}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
