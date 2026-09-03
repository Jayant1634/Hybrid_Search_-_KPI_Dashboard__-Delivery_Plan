#!/usr/bin/env bash
# Stop processes started by up.sh. Always exits 0.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

RUN_DIR=".run"

stop_pid() {
  local pid="$1"
  local waited
  if [[ -z "$pid" ]]; then
    return 0
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    return 0
  fi
  kill -TERM "$pid" 2>/dev/null || true
  waited=0
  while kill -0 "$pid" 2>/dev/null; do
    if [[ "$waited" -ge 5 ]]; then
      kill -KILL "$pid" 2>/dev/null || true
      break
    fi
    sleep 1
    waited=$((waited + 1))
  done
}

if [[ -d "$RUN_DIR" ]]; then
  shopt -s nullglob
  for pidfile in "$RUN_DIR"/*.pid; do
    pid="$(tr -d '[:space:]' < "$pidfile" || true)"
    stop_pid "$pid"
  done
  shopt -u nullglob
  rm -rf "$RUN_DIR"
fi

exit 0
