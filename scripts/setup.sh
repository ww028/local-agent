#!/usr/bin/env bash
# Public package sources only. Does not install Ollama or download model weights.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; assert (3, 11) <= sys.version_info[:2] <= (3, 14), "Use Python 3.11-3.14"'
command -v node >/dev/null
command -v npm >/dev/null
node -e 'if (Number(process.versions.node.split(".")[0]) < 20) process.exit(1)'
if [[ ! -d "$ROOT/backend/.venv" ]]; then
  "$PYTHON" -m venv "$ROOT/backend/.venv"
fi
"$ROOT/backend/.venv/bin/python" -m pip install --index-url https://pypi.org/simple -r "$ROOT/backend/requirements-dev.txt"
(cd "$ROOT/frontend" && npm ci --registry=https://registry.npmjs.org --ignore-scripts --no-audit --no-fund)
printf 'Dependencies ready. Start Ollama separately, then run bash scripts/dev.sh.\n'
