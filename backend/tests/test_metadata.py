from pathlib import Path

from app.index.metadata import IndexMetadata, is_up_to_date

MODEL = "all-MiniLM-L6-v2"
HASH = "abc123"


def _meta(built_at: str = "2026-09-03T00:00:00+00:00") -> IndexMetadata:
    return IndexMetadata.create(
        model=MODEL,
        dimension=384,
        corpus_hash=HASH,
        doc_count=6,
        built_at=built_at,
    )


def test_create_defaults_built_at_to_utc() -> None:
    meta = IndexMetadata.create(MODEL, 384, HASH, 6)
    assert meta.built_at.endswith("+00:00")


def test_save_load_roundtrip(tmp_path: Path) -> None:
    folder = tmp_path / "index"
    saved_path = _meta().save(folder)
    assert saved_path == folder / "metadata.json"
    assert saved_path.is_file()

    loaded = IndexMetadata.load(folder)
    assert loaded == _meta()


def test_up_to_date_when_hash_and_model_match(tmp_path: Path) -> None:
    _meta().save(tmp_path)
    assert is_up_to_date(tmp_path, HASH, MODEL) is True


def test_stale_when_metadata_missing(tmp_path: Path) -> None:
    assert is_up_to_date(tmp_path, HASH, MODEL) is False


def test_stale_when_corpus_hash_differs(tmp_path: Path) -> None:
    _meta().save(tmp_path)
    assert is_up_to_date(tmp_path, "different-hash", MODEL) is False


def test_stale_when_model_differs(tmp_path: Path) -> None:
    _meta().save(tmp_path)
    assert is_up_to_date(tmp_path, HASH, "other-model") is False
