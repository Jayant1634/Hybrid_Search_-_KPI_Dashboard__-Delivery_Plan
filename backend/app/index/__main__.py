"""Index CLI. Run from the repo root: ``python -m app.index``.

Reads the processed JSONL corpus, and if the saved index is stale (or ``--force``
is given) rebuilds the BM25 and vector indexes and writes ``metadata.json``.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import asdict
from pathlib import Path

from app.config import load_config
from app.ingest.writer import Doc, corpus_hash, read_jsonl
from app.search.bm25 import BM25Index
from app.search.embedder import Embedder
from app.search.vector import VectorIndex

from .metadata import IndexMetadata, is_up_to_date

_BM25_SUBDIR = "bm25"
_VECTOR_SUBDIR = "vector"


def _resolve_path(value: str | Path, *, repo_root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _embed_text(doc: Doc) -> str:
    return f"{doc.title} {doc.text}".strip()


def build_indexes(
    docs: list[Doc],
    index_dir: Path,
    embedder: Embedder,
    model: str,
) -> IndexMetadata:
    """Build BM25 + vector indexes into ``index_dir`` and write metadata."""
    index_dir.mkdir(parents=True, exist_ok=True)

    bm25 = BM25Index.build(asdict(doc) for doc in docs)
    bm25.save(index_dir / _BM25_SUBDIR)

    doc_ids = [doc.doc_id for doc in docs]
    vectors = embedder.encode([_embed_text(doc) for doc in docs])
    vector = VectorIndex.build(doc_ids, vectors)
    vector.save(index_dir / _VECTOR_SUBDIR)

    meta = IndexMetadata.create(
        model=model,
        dimension=embedder.dimension,
        corpus_hash=corpus_hash(docs),
        doc_count=len(docs),
    )
    meta.save(index_dir)
    return meta


def _build_parser(default_input: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build BM25 and vector indexes.")
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        help="processed docs.jsonl (default: config processed_dir/docs.jsonl)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="rebuild even if the saved index is up to date",
    )
    return parser


def main(argv: list[str] | None = None, embedder: Embedder | None = None) -> int:
    """CLI entry. Returns 0 on success (including the up-to-date short-circuit)."""
    settings = load_config()
    default_input = settings.processed_dir / "docs.jsonl"
    parser = _build_parser(default_input)
    args = parser.parse_args(argv)

    input_path = _resolve_path(args.input, repo_root=settings.repo_root)
    docs = read_jsonl(input_path)
    chash = corpus_hash(docs)
    model = settings.embedding_model
    index_dir = settings.index_dir

    if not args.force and is_up_to_date(index_dir, chash, model):
        print(f"up to date: {len(docs)} docs, model {model} -> skipping build")
        return 0

    if embedder is None:
        from app.search.embedder import SentenceTransformerEmbedder

        embedder = SentenceTransformerEmbedder()

    start = time.perf_counter()
    meta = build_indexes(docs, index_dir, embedder, model)
    elapsed = time.perf_counter() - start

    print(
        f"built index: model={meta.model} dim={meta.dimension} "
        f"count={meta.doc_count} seconds={elapsed:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
