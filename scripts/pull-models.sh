#!/usr/bin/env bash
# Pull local Ollama models. Defaults can be overridden in .env.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LLM_MODEL="${LLM_MODEL:-qwen3:14b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-bge-m3}"

# Load .env if present (do not fail if missing).
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

command -v ollama >/dev/null 2>&1 || { echo "Ollama is not installed."; exit 1; }

echo "==> Pulling chat model: ${LLM_MODEL}"
ollama pull "${LLM_MODEL}"

echo "==> Pulling embedding model: ${EMBEDDING_MODEL}"
ollama pull "${EMBEDDING_MODEL}"

echo "==> Models ready."
