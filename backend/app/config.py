"""Repo-root paths and HSS_ settings. No pydantic."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    raw_dir: Path
    processed_dir: Path
    index_dir: Path
    eval_dir: Path
    metrics_dir: Path
    sqlite_path: Path
    embedding_model: str
    default_alpha: float
    normalisation: str
    api_port: int
    ui_port: int
    rate_limit_per_minute: int
    log_level: str
    index_on_mismatch: str


def _is_repo_root(path: Path) -> bool:
    return (path / "up.sh").is_file() or (path / ".git").exists()


def _walk_up(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if _is_repo_root(candidate):
            return candidate
    return None


def find_repo_root(start: Path | None = None) -> Path:
    override = os.environ.get("HSS_REPO_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    found = _walk_up(start or Path.cwd())
    if found is None:
        found = _walk_up(Path(__file__).resolve().parent)
    if found is None:
        raise FileNotFoundError(
            "repo root not found: no up.sh or .git, and HSS_REPO_ROOT is unset"
        )
    return found


def _env_str(key: str, default: str) -> str:
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return value


def _env_int(key: str, default: int) -> int:
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _env_float(key: str, default: float) -> float:
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return float(value)


@lru_cache
def load_config() -> Settings:
    repo_root = find_repo_root()
    data_dir = repo_root / "data"
    return Settings(
        repo_root=repo_root,
        raw_dir=data_dir / "raw",
        processed_dir=data_dir / "processed",
        index_dir=data_dir / "index",
        eval_dir=data_dir / "eval",
        metrics_dir=data_dir / "metrics",
        sqlite_path=data_dir / "hss.sqlite",
        embedding_model=_env_str("HSS_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        default_alpha=_env_float("HSS_DEFAULT_ALPHA", 0.3),
        normalisation=_env_str("HSS_NORMALISATION", "minmax"),
        api_port=_env_int("HSS_API_PORT", 8000),
        ui_port=_env_int("HSS_UI_PORT", 5173),
        rate_limit_per_minute=_env_int("HSS_RATE_LIMIT_PER_MINUTE", 60),
        log_level=_env_str("HSS_LOG_LEVEL", "INFO"),
        index_on_mismatch=_env_str("HSS_INDEX_ON_MISMATCH", "fail"),
    )
