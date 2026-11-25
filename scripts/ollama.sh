#!/usr/bin/env bash
# Use an official Ollama CLI already installed on this machine.
# The project does not distribute binaries, keys or model weights.
set -euo pipefail
if command -v ollama >/dev/null 2>&1; then
  OLLAMA_BIN="$(command -v ollama)"
elif [[ -x /Applications/Ollama.app/Contents/Resources/ollama ]]; then
  OLLAMA_BIN=/Applications/Ollama.app/Contents/Resources/ollama
else
  printf 'Install official Ollama first, then retry.\n' >&2
  exit 1
fi
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_NO_CLOUD=1
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_CONTEXT_LENGTH=8192
export OLLAMA_KEEP_ALIVE=5m
if [[ $# -eq 0 ]]; then
  set -- serve
fi
exec "$OLLAMA_BIN" "$@"
