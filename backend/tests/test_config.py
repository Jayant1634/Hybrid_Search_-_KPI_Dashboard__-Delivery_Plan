from collections.abc import Iterator
from pathlib import Path

import pytest

from app.config import load_config

_HSS_KEYS = (
    "HSS_REPO_ROOT",
    "HSS_EMBEDDING_MODEL",
    "HSS_DEFAULT_ALPHA",
    "HSS_NORMALISATION",
    "HSS_API_PORT",
    "HSS_UI_PORT",
    "HSS_RATE_LIMIT_PER_MINUTE",
    "HSS_LOG_LEVEL",
)


@pytest.fixture(autouse=True)
def _uncache_settings() -> Iterator[None]:
    load_config.cache_clear()
    yield
    load_config.cache_clear()


def _clear_hss(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _HSS_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_repo_root_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_hss(monkeypatch)
    settings = load_config()
    expected = Path(__file__).resolve().parents[2]
    assert settings.repo_root == expected
    assert settings.raw_dir == expected / "data" / "raw"
    assert settings.processed_dir == expected / "data" / "processed"
    assert settings.index_dir == expected / "data" / "index"
    assert settings.eval_dir == expected / "data" / "eval"
    assert settings.metrics_dir == expected / "data" / "metrics"
    assert settings.sqlite_path == expected / "data" / "hss.sqlite"
    assert settings.embedding_model == "all-MiniLM-L6-v2"
    assert settings.default_alpha == 0.3
    assert settings.normalisation == "minmax"
    assert settings.api_port == 8000
    assert settings.ui_port == 5173
    assert settings.rate_limit_per_minute == 60
    assert settings.log_level == "INFO"


def test_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_hss(monkeypatch)
    monkeypatch.setenv("HSS_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("HSS_EMBEDDING_MODEL", "other-model")
    monkeypatch.setenv("HSS_DEFAULT_ALPHA", "0.7")
    monkeypatch.setenv("HSS_API_PORT", "9000")
    settings = load_config()
    root = tmp_path.resolve()
    assert settings.repo_root == root
    assert settings.raw_dir == root / "data" / "raw"
    assert settings.processed_dir == root / "data" / "processed"
    assert settings.index_dir == root / "data" / "index"
    assert settings.eval_dir == root / "data" / "eval"
    assert settings.metrics_dir == root / "data" / "metrics"
    assert settings.sqlite_path == root / "data" / "hss.sqlite"
    assert settings.embedding_model == "other-model"
    assert settings.default_alpha == 0.7
    assert settings.api_port == 9000
