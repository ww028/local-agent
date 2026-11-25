#!/usr/bin/env bash
# Install backend and frontend dependencies. Models are pulled separately
# via scripts/pull-models.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Checking prerequisites"
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node 20+ is required."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is required."; exit 1; }

echo "==> Backend: create venv and install dependencies"
cd "$ROOT/backend"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt

echo "==> Frontend: install dependencies"
cd "$ROOT/frontend"
npm install

echo "==> Done. Next: bash scripts/pull-models.sh, then bash scripts/dev.sh"
