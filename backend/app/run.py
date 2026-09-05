"""Start the API. From backend/: ``python run.py``. Or ``python -m app``."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

from app.config import find_repo_root, load_config

APP = "app.api.main:create_app"
HOST = "127.0.0.1"


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[7:].strip()
    if "=" not in stripped:
        return None
    key, _, value = stripped.partition("=")
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return key, value


def _iter_env_file(path: Path) -> Iterator[tuple[str, str]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(line)
        if parsed is not None:
            yield parsed


def load_dotenv(repo_root: Path | None = None) -> list[Path]:
    """Load ``backend/.env``. Existing keys win. Repo-root ``.env`` is ignored."""
    root = repo_root if repo_root is not None else find_repo_root()
    path = root / "backend" / ".env"
    if not path.is_file():
        return []
    for key, value in _iter_env_file(path):
        if key not in os.environ:
            os.environ[key] = value
    return [path]


def _venv_python(repo_root: Path) -> Path | None:
    if sys.platform == "win32":
        candidate = repo_root / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = repo_root / ".venv" / "bin" / "python"
    return candidate if candidate.is_file() else None


def _same_interpreter(candidate: Path) -> bool:
    try:
        return candidate.resolve() == Path(sys.executable).resolve()
    except OSError:
        return False


def _uvicorn_available() -> bool:
    try:
        import uvicorn  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def ensure_venv() -> None:
    """Re-exec with the repo .venv when this interpreter is missing uvicorn."""
    if _uvicorn_available():
        return
    python = _venv_python(find_repo_root())
    if python is None or _same_interpreter(python):
        raise SystemExit(
            "uvicorn is not installed. From the repo root run ./up.sh "
            "or install requirements into .venv."
        )
    os.execv(str(python), [str(python), "-m", "app", *sys.argv[1:]])


def main() -> None:
    """Run uvicorn with the factory app, local host, config port, reload on."""
    load_dotenv()
    load_config.cache_clear()
    ensure_venv()
    import uvicorn

    settings = load_config()
    uvicorn.run(
        APP,
        factory=True,
        host=HOST,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
