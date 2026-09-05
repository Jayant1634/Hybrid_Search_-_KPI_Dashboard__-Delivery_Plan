"""Re-run corpus fetch until every seed title is extracted or permanently skipped."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import fetch_corpus

BETWEEN_PASSES_SECONDS = 15.0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Loop fetch_corpus.py until all seed articles are on disk."
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=BETWEEN_PASSES_SECONDS,
        help="Seconds to wait between passes when titles are still missing (default 15).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
    args = parse_args(argv)
    repo = root if root is not None else fetch_corpus.repo_root()
    raw_dir = repo / "data" / "raw"
    seed_path = raw_dir / "seed_titles.txt"
    if not seed_path.is_file():
        print(f"seed file not found: {seed_path.as_posix()}", file=sys.stderr)
        return 1

    seed = fetch_corpus.read_seed(seed_path)
    pass_number = 0
    while True:
        pending = fetch_corpus.pending_rows(raw_dir, seed)
        if not pending:
            fetch_corpus.write_attribution(raw_dir)
            print("all titles extracted or permanently skipped")
            return 0
        pass_number += 1
        print(f"pass {pass_number}: {len(pending)} remaining")
        fetch_corpus.main([], root=repo)
        still = fetch_corpus.pending_rows(raw_dir, seed)
        if not still:
            print("all titles extracted or permanently skipped")
            return 0
        wait = max(args.wait, 0.0)
        print(f"{len(still)} still remaining, waiting {wait}s")
        if wait:
            time.sleep(wait)


if __name__ == "__main__":
    raise SystemExit(main())
