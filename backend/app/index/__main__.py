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
from app.search.embedder import Embedder, ProgressCallback
from app.search.vector import VectorIndex

from .chunk import chunk_document
from .metadata import IndexMetadata, is_up_to_date

_BM25_SUBDIR = "bm25"
_VECTOR_SUBDIR = "vector"
_GRANULARITIES = ("document", "sentence")


def _resolve_path(value: str | Path, *, repo_root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _embed_text(doc: Doc) -> str:
    return f"{doc.title} {doc.text}".strip()


def _embedding_inputs(
    docs: list[Doc],
    *,
    granularity: str,
    max_tokens: int,
) -> tuple[list[str], list[str]]:
    """Return parallel ``(doc_ids, texts)`` to embed for the given granularity.

    ``document`` yields one string per doc (``"{title} {text}"``).
    ``sentence`` yields one string per packed chunk, each tagged with its parent
    ``doc_id`` so many vectors can point back to the same document. Every doc
    contributes at least one vector so it stays retrievable.
    """
    if granularity != "sentence":
        return [doc.doc_id for doc in docs], [_embed_text(doc) for doc in docs]

    doc_ids: list[str] = []
    texts: list[str] = []
    for doc in docs:
        chunks = chunk_document(doc.text, max_tokens=max_tokens)
        if not chunks:
            chunks = [doc.title.strip() or doc.doc_id]
        for chunk in chunks:
            doc_ids.append(doc.doc_id)
            texts.append(f"{doc.title} {chunk}".strip())
    return doc_ids, texts


def build_indexes(
    docs: list[Doc],
    index_dir: Path,
    embedder: Embedder,
    model: str,
    *,
    granularity: str = "document",
    max_tokens: int | None = None,
    on_progress: ProgressCallback | None = None,
) -> IndexMetadata:
    """Build BM25 + vector indexes into ``index_dir`` and write metadata.

    BM25 is always document-level (the lexical side). The vector index follows
    ``granularity``: ``document`` stores one embedding per doc, ``sentence``
    stores one per packed chunk (``max_tokens`` per chunk, defaulting to the
    configured ``HSS_MAX_SEQ_LENGTH``) all mapped back to their ``doc_id``.
    """
    index_dir.mkdir(parents=True, exist_ok=True)
    if max_tokens is None:
        max_tokens = load_config().max_seq_length

    bm25 = BM25Index.build(asdict(doc) for doc in docs)
    bm25.save(index_dir / _BM25_SUBDIR)

    doc_ids, texts = _embedding_inputs(
        docs, granularity=granularity, max_tokens=max_tokens
    )
    vectors = embedder.encode(texts, on_progress=on_progress)
    vector = VectorIndex.build(doc_ids, vectors)
    vector.save(index_dir / _VECTOR_SUBDIR)

    meta = IndexMetadata.create(
        model=model,
        dimension=embedder.dimension,
        corpus_hash=corpus_hash(docs),
        doc_count=len(docs),
        granularity=granularity,
        vector_count=len(doc_ids),
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
    parser.add_argument(
        "--granularity",
        choices=_GRANULARITIES,
        default=None,
        help=(
            "vector index unit: 'document' (one vector per file) or 'sentence' "
            "(one vector per packed chunk, covering the whole file). "
            "Default: HSS_INDEX_GRANULARITY."
        ),
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
    granularity = args.granularity or settings.index_granularity
    index_dir = settings.index_dir

    if not args.force and is_up_to_date(
        index_dir, chash, model, granularity=granularity
    ):
        print(
            f"up to date: {len(docs)} docs, model {model}, "
            f"granularity {granularity} -> skipping build"
        )
        return 0

    if embedder is None:
        from app.search.embedder import SentenceTransformerEmbedder

        embedder = SentenceTransformerEmbedder()

    start = time.perf_counter()
    meta = build_indexes(docs, index_dir, embedder, model, granularity=granularity)
    elapsed = time.perf_counter() - start

    print(
        f"built index: model={meta.model} dim={meta.dimension} "
        f"count={meta.doc_count} granularity={meta.granularity} "
        f"vectors={meta.vector_count} seconds={elapsed:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
