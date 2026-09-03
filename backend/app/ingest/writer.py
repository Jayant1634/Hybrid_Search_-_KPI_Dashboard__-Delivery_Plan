"""Write and read the ingest JSONL corpus, with corpus hash and manifest."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

_DOC_ID_LENGTH = 12
_FIELDS = ("doc_id", "title", "text", "source", "created_at")


@dataclass(frozen=True)
class Doc:
    """A processed document (lld s6.1)."""

    doc_id: str
    title: str
    text: str
    source: str
    created_at: str


def make_doc_id(relative_path: str | Path) -> str:
    """Short, stable SHA1 of the POSIX relative file path."""
    posix = Path(relative_path).as_posix()
    digest = hashlib.sha1(posix.encode("utf-8")).hexdigest()
    return digest[:_DOC_ID_LENGTH]


def write_jsonl(docs: Iterable[Doc], path: Path) -> Path:
    """Write ``docs`` as one JSON object per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for doc in docs:
            handle.write(json.dumps(asdict(doc), ensure_ascii=False))
            handle.write("\n")
    return path


def read_jsonl(path: Path) -> list[Doc]:
    """Read a JSONL corpus back into ``Doc`` objects."""
    docs: list[Doc] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        docs.append(Doc(**{field: record[field] for field in _FIELDS}))
    return docs


def corpus_hash(docs: Iterable[Doc]) -> str:
    """SHA256 over each doc's id and text, ordered by id."""
    digest = hashlib.sha256()
    for doc in sorted(docs, key=lambda d: d.doc_id):
        digest.update(doc.doc_id.encode("utf-8"))
        digest.update(b"\0")
        digest.update(doc.text.encode("utf-8"))
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def write_manifest(
    docs: list[Doc],
    path: Path,
    input_dir: Path,
    *,
    built_at: str | None = None,
) -> Path:
    """Write manifest.json with count, corpus hash, build time, and input dir."""
    manifest = {
        "count": len(docs),
        "corpus_hash": corpus_hash(docs),
        "built_at": built_at or datetime.now(timezone.utc).isoformat(),
        "input_dir": input_dir.as_posix(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path
