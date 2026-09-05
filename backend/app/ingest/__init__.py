"""Ingest CLI. Run from the repo root: ``python -m app.ingest``."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.config import load_config

from .clean import clean_text, is_too_short, split_front_matter
from .split import split_sentences
from .writer import Doc, make_doc_id, write_jsonl, write_manifest

_TEXT_SUFFIXES = {".md", ".txt"}


def _resolve_path(value: str | Path, *, repo_root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _iter_source_files(input_dir: Path) -> list[Path]:
    files = [
        path
        for path in sorted(input_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in _TEXT_SUFFIXES
    ]
    return files


def _title_from(meta: dict[str, str], path: Path) -> str:
    title = meta.get("title", "").strip()
    return title or path.stem


def _source_from(meta: dict[str, str], relative: Path) -> str:
    source = meta.get("source", "").strip()
    return source or relative.as_posix()


def _created_at_from(meta: dict[str, str]) -> str:
    fetched = meta.get("fetched", "").strip()
    if fetched:
        if "T" in fetched:
            return fetched
        return f"{fetched}T00:00:00Z"
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_text(text: str, *, sentence_split: bool) -> str:
    if not sentence_split:
        return text
    return "\n".join(split_sentences(text))


def ingest(
    input_dir: Path,
    out_dir: Path,
    *,
    sentence_split: bool = False,
) -> Path | None:
    """Clean source files under ``input_dir`` into ``docs.jsonl`` + ``manifest.json``."""
    input_dir = input_dir.resolve()
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    docs: list[Doc] = []
    skipped = 0
    for path in _iter_source_files(input_dir):
        relative = path.relative_to(input_dir)
        raw = path.read_text(encoding="utf-8")
        meta, body = split_front_matter(raw)
        text = clean_text(body)
        if is_too_short(text):
            print(f"skipped: {relative.as_posix()} (too short, {len(text)} chars)")
            skipped += 1
            continue
        text = _format_text(text, sentence_split=sentence_split)
        docs.append(
            Doc(
                doc_id=make_doc_id(relative),
                title=_title_from(meta, path),
                text=text,
                source=_source_from(meta, relative),
                created_at=_created_at_from(meta),
            )
        )

    if not docs:
        print(f"wrote 0, skipped {skipped}")
        return None

    jsonl_path = write_jsonl(docs, out_dir / "docs.jsonl")
    write_manifest(docs, out_dir / "manifest.json", input_dir)
    print(f"wrote {len(docs)}, skipped {skipped} -> {jsonl_path.as_posix()}")
    return jsonl_path


def _build_parser(default_input: Path, default_out: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest raw docs into JSONL.")
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        help="directory of raw .md/.txt files (default: config raw_dir)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=default_out,
        help="output directory for docs.jsonl and manifest.json (default: config processed_dir)",
    )
    parser.add_argument(
        "--sentence-split",
        action="store_true",
        help="store cleaned text as one sentence per line",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Returns 0 on success, 1 if nothing was written."""
    settings = load_config()
    parser = _build_parser(settings.raw_dir, settings.processed_dir)
    args = parser.parse_args(argv)
    input_dir = _resolve_path(args.input, repo_root=settings.repo_root)
    out_dir = _resolve_path(args.out, repo_root=settings.repo_root)
    written = ingest(input_dir, out_dir, sentence_split=args.sentence_split)
    return 0 if written is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
