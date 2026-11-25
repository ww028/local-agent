#!/usr/bin/env bash
# Offline start after setup. Only manages children created by this invocation.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/backend/.venv/bin/python"
if [[ ! -x "$PYTHON" || ! -f "$ROOT/frontend/dist/index.html" ]]; then
  printf 'Run bash scripts/setup.sh while online first.\n' >&2
  exit 1
fi
OLLAMA_PID=""
API_PID=""
cleanup() {
  [[ -z "$API_PID" ]] || kill "$API_PID" 2>/dev/null || true
  [[ -z "$OLLAMA_PID" ]] || kill "$OLLAMA_PID" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 0' INT TERM
if ! "$PYTHON" -c 'import httpx; r=httpx.get("http://127.0.0.1:11434/api/version",trust_env=False,timeout=2);r.raise_for_status()' >/dev/null 2>&1; then
  bash "$ROOT/scripts/ollama.sh" serve &
  OLLAMA_PID=$!
  sleep 3
fi
(cd "$ROOT/backend" && exec "$PYTHON" run.py) &
API_PID=$!
printf 'Local workbench: http://127.0.0.1:8000 (or configured BACKEND_PORT)\n'
wait "$API_PID"
