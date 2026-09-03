import json
from pathlib import Path

from app.ingest.writer import (
    Doc,
    corpus_hash,
    make_doc_id,
    read_jsonl,
    write_jsonl,
    write_manifest,
)


def _sample_docs() -> list[Doc]:
    return [
        Doc(
            doc_id=make_doc_id("volcanoes/volcano.md"),
            title="Volcano",
            text="A volcano erupts lava and ash.",
            source="https://simple.wikipedia.org/wiki/Volcano",
            created_at="2026-09-03T00:00:00Z",
        ),
        Doc(
            doc_id=make_doc_id("planets/mars.md"),
            title="Mars",
            text="Mars is the red planet.",
            source="https://simple.wikipedia.org/wiki/Mars",
            created_at="2026-09-03T00:00:00Z",
        ),
    ]


def test_round_trip(tmp_path: Path) -> None:
    docs = _sample_docs()
    out = write_jsonl(docs, tmp_path / "docs.jsonl")
    assert read_jsonl(out) == docs


def test_doc_id_is_stable_across_runs() -> None:
    assert make_doc_id("volcanoes/volcano.md") == make_doc_id("volcanoes/volcano.md")
    assert make_doc_id(Path("volcanoes") / "volcano.md") == make_doc_id(
        "volcanoes/volcano.md"
    )
    assert make_doc_id("volcanoes/volcano.md") != make_doc_id("planets/mars.md")


def test_hash_changes_when_one_character_changes() -> None:
    docs = _sample_docs()
    before = corpus_hash(docs)
    changed = list(docs)
    changed[0] = Doc(**{**docs[0].__dict__, "text": docs[0].text + "!"})
    after = corpus_hash(changed)
    assert before != after


def test_hash_is_order_independent() -> None:
    docs = _sample_docs()
    assert corpus_hash(docs) == corpus_hash(list(reversed(docs)))


def test_manifest_fields(tmp_path: Path) -> None:
    docs = _sample_docs()
    input_dir = tmp_path / "data" / "raw"
    path = write_manifest(
        docs,
        tmp_path / "manifest.json",
        input_dir,
        built_at="2026-09-03T10:00:00+00:00",
    )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["count"] == 2
    assert manifest["corpus_hash"] == corpus_hash(docs)
    assert manifest["built_at"] == "2026-09-03T10:00:00+00:00"
    assert manifest["input_dir"] == input_dir.as_posix()
