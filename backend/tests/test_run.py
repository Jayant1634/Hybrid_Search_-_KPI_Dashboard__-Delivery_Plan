import os
import sys
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import load_config
from app.run import APP, HOST, ensure_venv, load_dotenv, main


@pytest.fixture(autouse=True)
def _uncache_settings() -> Iterator[None]:
    load_config.cache_clear()
    yield
    load_config.cache_clear()


def test_main_starts_uvicorn_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.run.load_dotenv", lambda: [])
    with patch("uvicorn.run") as run:
        main()
    run.assert_called_once_with(
        APP,
        factory=True,
        host=HOST,
        port=8000,
        reload=True,
    )


def test_main_uses_hss_api_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.run.load_dotenv", lambda: [])
    monkeypatch.setenv("HSS_API_PORT", "9000")
    load_config.cache_clear()
    with patch("uvicorn.run") as run:
        main()
    run.assert_called_once_with(
        APP,
        factory=True,
        host=HOST,
        port=9000,
        reload=True,
    )


def test_load_dotenv_reads_backend_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HSS_REPO_ROOT", str(tmp_path))
    monkeypatch.delenv("HSS_API_PORT", raising=False)
    monkeypatch.delenv("HSS_EMBEDDING_MODEL", raising=False)
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    (backend_dir / ".env").write_text(
        "# comment\n"
        "export HSS_API_PORT=8123\n"
        'HSS_EMBEDDING_MODEL="sentence-transformers/paraphrase-albert-small-v2"\n',
        encoding="utf-8",
    )
    loaded = load_dotenv()
    assert loaded == [backend_dir / ".env"]
    assert os.environ["HSS_API_PORT"] == "8123"
    assert (
        os.environ["HSS_EMBEDDING_MODEL"]
        == "sentence-transformers/paraphrase-albert-small-v2"
    )


def test_load_dotenv_ignores_root_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HSS_REPO_ROOT", str(tmp_path))
    monkeypatch.delenv("HSS_EMBEDDING_MODEL", raising=False)
    (tmp_path / ".env").write_text(
        "HSS_EMBEDDING_MODEL=root-model\n", encoding="utf-8"
    )
    loaded = load_dotenv()
    assert loaded == []
    assert "HSS_EMBEDDING_MODEL" not in os.environ


def test_up_sh_sources_backend_env() -> None:
    path = Path(__file__).resolve().parents[2] / "up.sh"
    text = path.read_text(encoding="utf-8")
    assert "./backend/.env" in text
    assert ". ./.env" not in text


def test_load_dotenv_does_not_override_process_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HSS_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("HSS_API_PORT", "9000")
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    (backend_dir / ".env").write_text("HSS_API_PORT=8123\n", encoding="utf-8")
    load_dotenv()
    assert os.environ["HSS_API_PORT"] == "9000"


def test_load_dotenv_missing_files_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HSS_REPO_ROOT", str(tmp_path))
    assert load_dotenv() == []


def test_main_uses_backend_env_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HSS_REPO_ROOT", str(tmp_path))
    monkeypatch.delenv("HSS_API_PORT", raising=False)
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    (backend_dir / ".env").write_text("HSS_API_PORT=8123\n", encoding="utf-8")
    load_config.cache_clear()
    with patch("uvicorn.run") as run:
        main()
    run.assert_called_once_with(
        APP,
        factory=True,
        host=HOST,
        port=8123,
        reload=True,
    )


def test_package_main_delegates_to_run() -> None:
    import app.__main__ as package_main

    assert package_main.main is main


def test_backend_run_py_exists() -> None:
    path = Path(__file__).resolve().parents[1] / "run.py"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "from app.run import main" in text


def test_ensure_venv_noop_when_uvicorn_present() -> None:
    ensure_venv()


def test_ensure_venv_reexecs_repo_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HSS_REPO_ROOT", str(tmp_path))
    if sys.platform == "win32":
        venv_py = tmp_path / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = tmp_path / ".venv" / "bin" / "python"
    venv_py.parent.mkdir(parents=True)
    venv_py.write_bytes(b"")
    monkeypatch.setattr("app.run._uvicorn_available", lambda: False)
    monkeypatch.setattr("app.run.sys.argv", ["app", "--help"])
    called: dict[str, object] = {}

    def fake_execv(path: str, args: list[str]) -> None:
        called["path"] = path
        called["args"] = args
        raise SystemExit(0)

    monkeypatch.setattr("app.run.os.execv", fake_execv)
    with pytest.raises(SystemExit) as exc:
        ensure_venv()
    assert exc.value.code == 0
    assert called["path"] == str(venv_py)
    assert called["args"] == [str(venv_py), "-m", "app", "--help"]


def test_ensure_venv_errors_when_venv_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HSS_REPO_ROOT", str(tmp_path))
    monkeypatch.setattr("app.run._uvicorn_available", lambda: False)
    with pytest.raises(SystemExit, match="uvicorn is not installed"):
        ensure_venv()
