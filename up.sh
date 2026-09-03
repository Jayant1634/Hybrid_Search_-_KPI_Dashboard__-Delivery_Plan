#!/usr/bin/env bash
# Create the local env if needed, build missing artifacts, and start API + UI.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

API_PORT="${HSS_API_PORT:-8000}"
UI_PORT="${HSS_UI_PORT:-5173}"
RUN_DIR=".run"
TORCH_CPU_INDEX="https://download.pytorch.org/whl/cpu"
REQ_MARKER=".venv/.requirements.sha256"
CLEANED=0

require_python_311() {
  local py="$1"
  local ver
  if ! "$py" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"; then
    ver="$("$py" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>/dev/null || true)"
    if [[ -n "$ver" ]]; then
      echo "error: Python 3.11 or newer is required (found ${ver})" >&2
    else
      echo "error: Python 3.11 or newer is required" >&2
    fi
    exit 1
  fi
}

resolve_system_python() {
  local candidate ver seen=""
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      ver="$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>/dev/null || true)"
      if [[ -n "$ver" ]]; then
        seen="$ver"
        if "$candidate" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"; then
          printf '%s\n' "$candidate"
          return 0
        fi
      fi
    fi
  done
  if [[ -n "$seen" ]]; then
    echo "error: Python 3.11 or newer is required (found ${seen})" >&2
  else
    echo "error: Python 3.11 or newer is required" >&2
  fi
  exit 1
}

resolve_venv_python() {
  if [[ -x .venv/bin/python ]]; then
    printf '%s\n' ".venv/bin/python"
  elif [[ -x .venv/Scripts/python.exe ]]; then
    printf '%s\n' ".venv/Scripts/python.exe"
  else
    echo "error: .venv python not found; expected .venv/bin/python or .venv/Scripts/python.exe" >&2
    exit 1
  fi
}

stop_pid() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    return 0
  fi
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}

cleanup() {
  local pidfile pid
  if [[ "$CLEANED" -eq 1 ]]; then
    return 0
  fi
  CLEANED=1
  if [[ -d "$RUN_DIR" ]]; then
    for pidfile in "$RUN_DIR"/*.pid; do
      [[ -e "$pidfile" ]] || continue
      pid="$(tr -d '[:space:]' < "$pidfile" || true)"
      stop_pid "$pid"
      rm -f "$pidfile"
    done
  fi
}

if [[ ! -d .venv ]]; then
  SYS_PYTHON="$(resolve_system_python)"
  echo "creating .venv with $SYS_PYTHON"
  "$SYS_PYTHON" -m venv .venv
  PYTHON="$(resolve_venv_python)"
  "$PYTHON" -m pip install --upgrade pip
else
  PYTHON="$(resolve_venv_python)"
  require_python_311 "$PYTHON"
fi

echo "using $PYTHON"

requirements_hash() {
  "$PYTHON" -c "import hashlib; from pathlib import Path; print(hashlib.sha256(Path('requirements.txt').read_bytes()).hexdigest())"
}

REQ_HASH="$(requirements_hash)"
if [[ -f "$REQ_MARKER" ]] && [[ "$(tr -d '[:space:]' < "$REQ_MARKER")" == "$REQ_HASH" ]]; then
  echo "requirements.txt unchanged; skipping pip install"
else
  echo "requirements.txt changed or marker missing; installing"
  "$PYTHON" -m pip install torch==2.14.0 --index-url "$TORCH_CPU_INDEX"
  "$PYTHON" -m pip install -r requirements.txt
  "$PYTHON" -m pip install -e backend
  printf '%s\n' "$REQ_HASH" > "$REQ_MARKER"
fi

if [[ ! -f data/processed/docs.jsonl ]]; then
  echo "ingest artifacts missing; running ingest"
  "$PYTHON" -m app.ingest --input data/raw --out data/processed
else
  echo "ingest artifacts present; skipping ingest"
fi

if [[ ! -f data/index/metadata.json ]]; then
  echo "index artifacts missing; running index"
  "$PYTHON" -m app.index --input data/processed/docs.jsonl
else
  echo "index artifacts present; skipping index"
fi

if [[ ! -d frontend/node_modules ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "error: npm is required to install frontend dependencies" >&2
    exit 1
  fi
  echo "frontend/node_modules missing; running npm ci"
  npm ci --prefix frontend
else
  echo "frontend/node_modules present; skipping npm ci"
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "error: npm is required to start the Vite dev server" >&2
  exit 1
fi

mkdir -p "$RUN_DIR"
trap cleanup EXIT INT TERM

"$PYTHON" -m uvicorn app.api.main:create_app --factory --host 127.0.0.1 --port "$API_PORT" &
echo $! > "$RUN_DIR/api.pid"

if [[ -f frontend/node_modules/vite/bin/vite.js ]] && command -v node >/dev/null 2>&1; then
  (cd frontend && exec node ./node_modules/vite/bin/vite.js --host 127.0.0.1 --port "$UI_PORT" --strictPort) &
else
  (cd frontend && exec npm run dev -- --host 127.0.0.1 --port "$UI_PORT" --strictPort) &
fi
echo $! > "$RUN_DIR/ui.pid"

echo "API: http://127.0.0.1:${API_PORT}"
echo "UI: http://127.0.0.1:${UI_PORT}"

wait || true
