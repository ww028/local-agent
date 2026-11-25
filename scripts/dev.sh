#!/usr/bin/env bash
# One terminal runs both single-user services. No model download or external API.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/backend/.venv/bin/python"
if [[ ! -x "$PYTHON" || ! -d "$ROOT/frontend/node_modules" ]]; then
  printf 'Run bash scripts/setup.sh first.\n' >&2
  exit 1
fi
(cd "$ROOT/backend" && exec "$PYTHON" run.py) &
BACKEND_PID=$!
(cd "$ROOT/frontend" && exec npm run dev) &
FRONTEND_PID=$!
cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 0' INT TERM
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done
printf 'A service exited; stopping the workbench.\n' >&2
exit 1
