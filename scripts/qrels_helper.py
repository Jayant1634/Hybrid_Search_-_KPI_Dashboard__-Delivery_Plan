"""Print top-20 doc ids and titles per query so qrels can be labelled by hand.

Reads a text file (one query per line), loads ``SearchService``, and prints
each hit's ``doc_id`` and title. Nothing is written back.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Protocol

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

TOP_K = 20


class Hit(Protocol):
    doc_id: str
    title: str


class Searcher(Protocol):
    def search(self, query: str, top_k: int = TOP_K) -> list[Hit]: ...


class Service(Protocol):
    searcher: Searcher


def read_queries(path: Path) -> list[str]:
    """Return non-blank, stripped lines from ``path``."""
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def format_block(query: str, results: list[Hit]) -> str:
    """One query header plus ranked ``doc_id`` and title lines."""
    lines = [f"=== {query} ==="]
    for rank, hit in enumerate(results, start=1):
        lines.append(f"{rank}. {hit.doc_id}\t{hit.title}")
    return "\n".join(lines)


def label_queries(
    service: Service,
    queries: list[str],
    *,
    top_k: int = TOP_K,
) -> str:
    """Search each query and format the top hits for hand labelling."""
    blocks = [
        format_block(query, service.searcher.search(query, top_k=top_k))
        for query in queries
    ]
    return "\n\n".join(blocks)


def main(argv: list[str] | None = None) -> int:
    """Load ``SearchService`` and print top-20 ids and titles per query."""
    parser = argparse.ArgumentParser(
        description="Print top-20 doc ids and titles for hand-labelling qrels."
    )
    parser.add_argument(
        "queries",
        type=Path,
        help="text file, one query per line",
    )
    args = parser.parse_args(argv)
    queries_path = args.queries
    if not queries_path.is_file():
        print(f"queries file not found: {queries_path}", file=sys.stderr)
        return 1

    from app.api.deps import SearchService
    from app.search.embedder import SentenceTransformerEmbedder

    service = SearchService.load(SentenceTransformerEmbedder())
    print(label_queries(service, read_queries(queries_path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
