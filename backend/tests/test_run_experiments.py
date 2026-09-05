"""Structural and (when bash is present) dry-run checks for run_experiments.sh."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "run_experiments.sh"


def _is_wsl_launcher(path: Path) -> bool:
    lowered = path.resolve().as_posix().lower()
    return lowered.endswith("/system32/bash.exe") or "/windowsapps/bash.exe" in lowered


def _find_bash() -> str | None:
    seen: set[str] = set()
    candidates: list[Path] = []
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if directory:
            candidates.append(Path(directory) / "bash.exe")
            candidates.append(Path(directory) / "bash")
    program_files = os.environ.get("ProgramFiles", "")
    if program_files:
        candidates.append(Path(program_files) / "Git" / "bin" / "bash.exe")
    which = shutil.which("bash")
    if which:
        candidates.append(Path(which))
    for candidate in candidates:
        if not candidate.is_file():
            continue
        key = str(candidate.resolve()).lower()
        if key in seen or _is_wsl_launcher(candidate):
            continue
        seen.add(key)
        return str(candidate)
    return None


_BASH = _find_bash()


def _script_text() -> str:
    return _SCRIPT.read_text(encoding="utf-8")


def test_script_uses_strict_bash_and_venv_detection() -> None:
    text = _script_text()
    assert text.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in text
    assert ".venv/bin/python" in text
    assert ".venv/Scripts/python.exe" in text
    assert text.index(".venv/bin/python") < text.index(".venv/Scripts/python.exe")
    assert "./backend/.env" in text
    assert ". ./.env" not in text


def test_script_is_lf() -> None:
    assert b"\r" not in _SCRIPT.read_bytes()


def test_script_covers_required_experiments() -> None:
    text = _script_text()
    for alpha in ("0", "0.3", "0.5", "0.7", "1"):
        assert alpha in text
    assert "minmax" in text
    assert "zscore" in text
    assert "paraphrase-albert-small-v2" in text
    assert "--sentence-split" in text
    assert "app.eval" in text
    assert "app.index" in text
    assert "app.ingest" in text
    assert "banner" in text
    ingest_split = text.index("app.ingest --sentence-split")
    ingest_restore = text.rindex("app.ingest")
    assert ingest_split < ingest_restore


@pytest.mark.skipif(_BASH is None, reason="bash not on PATH")
def test_script_syntax() -> None:
    result = subprocess.run(
        [_BASH, "-n", str(_SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def _write_stub_python(path: Path, log_path: Path) -> None:
    launcher = (
        "import os\n"
        "import sys\n"
        f"log = {str(log_path.resolve())!r}\n"
        "model = os.environ.get('HSS_EMBEDDING_MODEL', '')\n"
        "with open(log, 'a', encoding='utf-8') as handle:\n"
        "    handle.write(model + '\\t' + ' '.join(sys.argv[1:]) + '\\n')\n"
    )
    stub_py = path.parent.parent.parent / "_stub_python.py"
    stub_py.write_text(launcher, encoding="utf-8", newline="\n")
    body = (
        "#!/usr/bin/env bash\n"
        f'exec {sys.executable!r} {str(stub_py.resolve())!r} "$@"\n'
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body.encode("utf-8"))
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _copy_script(tmp_path: Path) -> Path:
    dest_dir = tmp_path / "scripts"
    dest_dir.mkdir()
    dest = dest_dir / "run_experiments.sh"
    dest.write_bytes(_SCRIPT.read_bytes())
    dest.chmod(dest.stat().st_mode | stat.S_IXUSR)
    return dest


@pytest.mark.skipif(_BASH is None, reason="bash not on PATH")
def test_missing_venv_exits_one(tmp_path: Path) -> None:
    dest = _copy_script(tmp_path)
    result = subprocess.run(
        [_BASH, str(dest)],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 1
    assert ".venv/bin/python" in result.stderr
    assert ".venv/Scripts/python.exe" in result.stderr


@pytest.mark.skipif(_BASH is None, reason="bash not on PATH")
def test_run_sequence_with_stub_python(tmp_path: Path) -> None:
    dest = _copy_script(tmp_path)
    log_path = tmp_path / "commands.log"
    stub = tmp_path / ".venv" / "bin" / "python"
    _write_stub_python(stub, log_path)

    env = os.environ.copy()
    env.pop("HSS_EMBEDDING_MODEL", None)
    result = subprocess.run(
        [_BASH, str(dest)],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "== eval alpha=0 normalization=minmax" in result.stdout
    assert "== eval alpha=0.5 normalization=zscore" in result.stdout
    assert "== rebuild index model=paraphrase-albert-small-v2" in result.stdout
    assert "== ingest --sentence-split" in result.stdout
    assert "== ingest (restore document-level)" in result.stdout

    lines = log_path.read_text(encoding="utf-8").splitlines()
    default = "all-MiniLM-L6-v2"
    alt = "paraphrase-albert-small-v2"
    expected = [
        f"\t-m app.eval --alpha 0 --normalization minmax --model {default} --preprocessing none --tag alpha-0",
        f"\t-m app.eval --alpha 0.3 --normalization minmax --model {default} --preprocessing none --tag alpha-0.3",
        f"\t-m app.eval --alpha 0.5 --normalization minmax --model {default} --preprocessing none --tag alpha-0.5",
        f"\t-m app.eval --alpha 0.7 --normalization minmax --model {default} --preprocessing none --tag alpha-0.7",
        f"\t-m app.eval --alpha 1 --normalization minmax --model {default} --preprocessing none --tag alpha-1",
        f"\t-m app.eval --alpha 0.5 --normalization zscore --model {default} --preprocessing none --tag zscore-0.5",
        f"{alt}\t-m app.index --force",
        f"{alt}\t-m app.eval --alpha 0.5 --normalization minmax --model {alt} --preprocessing none --tag model-{alt}",
        f"{default}\t-m app.index --force",
        "\t-m app.ingest --sentence-split",
        f"{default}\t-m app.index --force",
        f"\t-m app.eval --alpha 0.5 --normalization minmax --model {default} --preprocessing sentence-split --tag sentence-split",
        "\t-m app.ingest",
        f"{default}\t-m app.index --force",
    ]
    assert lines == expected


@pytest.mark.skipif(_BASH is None, reason="bash not on PATH")
def test_prefers_unix_venv_python(tmp_path: Path) -> None:
    dest = _copy_script(tmp_path)
    log_path = tmp_path / "commands.log"
    _write_stub_python(tmp_path / ".venv" / "bin" / "python", log_path)
    win = tmp_path / ".venv" / "Scripts" / "python.exe"
    win.parent.mkdir(parents=True)
    win.write_bytes(b"not used")

    env = os.environ.copy()
    env.pop("HSS_EMBEDDING_MODEL", None)
    result = subprocess.run(
        [_BASH, str(dest)],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    text = log_path.read_text(encoding="utf-8")
    assert "-m app.eval" in text
    assert win.read_bytes() == b"not used"
