# Setup (local Agent workbench)

## Prerequisites

- Python 3.11–3.14. Python 3.14 is used for local phase-1 tests; CI uses 3.12.
  Knowledge/LanceDB dependencies are installed by setup and tested locally on 3.14.
- Node **20.19+ or 22.12+** (Vite 7), npm.
- Ollama installed separately and running locally. Only installed local chat
  models are accepted; cloud stubs and embedding-only models are blocked.

## Start

```bash
git clone https://github.com/ww028/local-agent.git
cd local-agent
cp .env.example .env
bash scripts/setup.sh
# In a separate terminal, if Ollama is not already running:
bash scripts/ollama.sh serve
# Download a chat model while online, before offline use:
# bash scripts/ollama.sh pull qwen3:14b
# After downloading models, use one-command packaged local start:
bash scripts/start.sh
```

Open **http://127.0.0.1:8000** (or configured BACKEND_PORT).
Select an installed chat model, send a message, stop generation, open a saved
conversation or create a new one. Changing models applies to the next message.
Model selection verifies capabilities before any message is sent to Ollama.
No weights are downloaded by `setup.sh`, the app or its model-list endpoint.

The embedding model is required for knowledge indexing/search, but not free chat.
Download `bge-m3` using `bash scripts/ollama.sh pull bge-m3`. Markdown/TXT upload
returns pending/indexing/ready/error status; failures can be reindexed. The Agent
mode exposes only imported knowledge reading/search and arithmetic calculation.
Model steps and tool results are stored and can be reopened from a message.

## Background tasks

Open **/jobs** from the task-center navigation. Submit an instruction and select
an installed local model. The backend accepts it immediately, persists it in
SQLite and executes it independently of the submitting request. The page polls
status/results every two seconds; refresh, navigation and closing the page do
not cancel jobs. Cancel queued/running work explicitly. Retry creates a new job
only for failed/cancelled/interrupted work and preserves the old record.

Local diagnostics are disabled by default. To ask which process listens on a
TCP port, explicitly check the per-task diagnostic box. This exposes only
`check_port` and `system_info`; macOS/Linux port lookup requires `lsof`. No sudo,
arbitrary commands, process termination, GUI control or file write is exposed.
A lookup error is not proof that a port is free. Tool facts remain in collapsed
execution details, separately from the model answer; knowledge citations link
back to imported documents.

Keep the computer awake and backend process running. No system service or login
item is installed. On service restart queued jobs resume; active jobs become
interrupted and are never replayed automatically. Run one backend worker only.
Up to 32 pending/active jobs, 2,000-character instructions and 180 seconds per
execution are supported, within the Agent's six-step/eight-tool/120-second loop.

## Configuration and data

The backend reads the repository-root `.env`, regardless of its working directory.
Relative data paths resolve against the repository root. Defaults bind to
loopback only. The frontend development proxy reads `BACKEND_PORT` and
`FRONTEND_PORT` from that same configuration file; no server secrets are exposed
as frontend environment variables.

`NUM_CTX` reserves `NUM_PREDICT` tokens for output. Input budgeting conservatively
uses UTF-8 bytes plus overhead, not an exact model tokenizer. Older completed
turns are omitted as pairs when they exceed the budget. Oversized new messages
are rejected. The model's actual native context limit must be checked separately.

SQLite stores messages and generation states: complete / generating / error /
interrupted. Abandoned generations become interrupted on startup. Cancellation
stores partial output; failed/interrupted turns do not enter future prompts.
The API accepts only **one generation at a time**; run **one backend worker**.
Do not run two instances against the same database.

`.env`, `.venv`, `node_modules`, databases and runtime data are not committed.
Back up `data/` with the application stopped. This is single-user developer
software, not an authenticated multi-user or internet-facing service.

## Offline and security boundary

Install packages and download weights while online; runtime chat is local.
Ollama HTTP clients ignore environment proxies and reject non-loopback URLs.
Browser-origin and Host checks reject unexpected sites; output rendering does
not load remote images or enable navigation links. These are basic safeguards,
not a security sandbox or enterprise certification. No telemetry or contribution
collector is configured by this project. Never upload private documents into
issues, test fixtures, logs, or repository history.

## Test

```bash
cd backend
.venv/bin/python -m pytest -q
.venv/bin/ruff check app tests
cd ../frontend
npm test
npm run build
```

The local launcher `scripts/ollama.sh` accepts the CLI in PATH or the official
macOS application's embedded CLI. It binds to loopback, disables cloud, allows
one loaded model and one generation, and unloads idle weights after five minutes.
No login item or automatic system startup is installed by this script.

Automated tests use fake models and HTTP transports and do not require Ollama,
network access or weights. For a real-model smoke test after starting services:
`backend/.venv/bin/python scripts/smoke-local.py` from the repository root.
The smoke test uses fictional prompts; measurements are saved in gitignored
`data/`. Physical offline operation and broad model quality remain separate
acceptance items.
The packaged local UI is served by FastAPI on BACKEND_PORT with its API.
For hot-reload development use `bash scripts/dev.sh` on FRONTEND_PORT (default5173).
Both modes remain single-user local deployments, not internet production services.
