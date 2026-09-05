"""Start the API. From backend/: ``python run.py``. Or ``python -m app``."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from app.config import find_repo_root, load_config

APP = "app.api.main:create_app"
HOST = "127.0.0.1"


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
