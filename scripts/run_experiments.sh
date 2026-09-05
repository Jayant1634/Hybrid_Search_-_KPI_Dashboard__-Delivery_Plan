#!/usr/bin/env bash
# Run the FR-21 experiment set and restore the default ingest + index.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f backend/.env ]]; then
  set -a
  # shellcheck disable=SC1091
  . ./backend/.env
  set +a
fi

if [[ -x .venv/bin/python ]]; then
  PYTHON=".venv/bin/python"
elif [[ -x .venv/Scripts/python.exe ]]; then
  PYTHON=".venv/Scripts/python.exe"
else
  echo "error: .venv python not found; expected .venv/bin/python or .venv/Scripts/python.exe" >&2
  exit 1
fi

DEFAULT_MODEL="${HSS_EMBEDDING_MODEL:-all-MiniLM-L6-v2}"
ALT_MODEL="paraphrase-albert-small-v2"

banner() {
  echo
  echo "========================================"
  echo "== $*"
  echo "========================================"
}

run_eval() {
  local alpha="$1"
  local normalization="$2"
  local model="$3"
  local preprocessing="$4"
  local tag="$5"
  "$PYTHON" -m app.eval \
    --alpha "$alpha" \
    --normalization "$normalization" \
    --model "$model" \
    --preprocessing "$preprocessing" \
    --tag "$tag"
}

rebuild_index() {
  local model="$1"
  HSS_EMBEDDING_MODEL="$model" "$PYTHON" -m app.index --force
}

echo "using $PYTHON (default model ${DEFAULT_MODEL})"

for alpha in 0 0.3 0.5 0.7 1; do
  banner "eval alpha=${alpha} normalization=minmax"
  run_eval "$alpha" minmax "$DEFAULT_MODEL" none "alpha-${alpha}"
done

banner "eval alpha=0.5 normalization=zscore"
run_eval 0.5 zscore "$DEFAULT_MODEL" none "zscore-0.5"

banner "rebuild index model=${ALT_MODEL}"
rebuild_index "$ALT_MODEL"

banner "eval model=${ALT_MODEL}"
HSS_EMBEDDING_MODEL="$ALT_MODEL" run_eval 0.5 minmax "$ALT_MODEL" none "model-${ALT_MODEL}"

banner "rebuild index model=${DEFAULT_MODEL}"
rebuild_index "$DEFAULT_MODEL"

banner "ingest --sentence-split"
"$PYTHON" -m app.ingest --sentence-split

banner "rebuild index (sentence-split corpus)"
rebuild_index "$DEFAULT_MODEL"

banner "eval preprocessing=sentence-split"
run_eval 0.5 minmax "$DEFAULT_MODEL" sentence-split "sentence-split"

banner "ingest (restore document-level)"
"$PYTHON" -m app.ingest

banner "rebuild index (restore)"
rebuild_index "$DEFAULT_MODEL"
