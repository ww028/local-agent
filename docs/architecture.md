# Architecture

local-agent is a single-user, local-first Web workbench. Current runtime paths
are described here; some scaffold interfaces remain reserved, not production
features. The application is not a multi-tenant service or a security sandbox.

## Runtime layers

- React/TypeScript/Vite: chat, documents, background jobs and execution history.
- FastAPI: loopback API, SSE chat and packaged static Web UI.
- `ollama_client.py`: installed-model validation, streaming chat, structured
  tool decisions and dense embedding calls to local Ollama only.
- `knowledge.py` + `ingest/chunker.py`: upload validation, heading/fence-aware
  chunking, serial indexing, status and hybrid retrieval.
- `agent/toolbox.py` + `agent/executor.py`: registered read-only tools,
  argument checks, bounded model/tool/observation loop and source labeling.
- `jobs.py`: lifespan-owned worker, model-lock scheduling and task lifecycle.
- `store/`: SQLite business records and rebuildable LanceDB vector index.

## RAG data flow

1. UTF-8 Markdown/TXT upload → local random-ID file and SQLite document record.
2. Heading/fence-aware chunks → local dense embeddings → LanceDB index.
3. Query → cosine vector candidates + SQLite FTS5 English terms/Chinese bigrams.
4. RRF fusion and ready-document filtering → bounded evidence context.
5. Local model answer → persisted labeled citations and links to source chunks.

SQLite is the document/chunk/status authority. LanceDB is a rebuildable vector
copy, not a second independent business database. Top-K evidence retrieval does
not guarantee full-document summarization or exhaustive cross-document review.

## Agent execution

The current executor uses local Ollama tool decisions rather than a separate
implemented planning service. Tools include imported-knowledge search/read and
bounded arithmetic. Per-task opt-in adds `check_port` and `system_info` only.
Successful actual tool calls satisfy explicit required-tool conditions; errors
or a model's verbal claim of action do not. Tool outputs/document content are
untrusted evidence, not permission grants. Sources, steps and final results are
recorded locally. Step/tool/time/input budgets and cancellation bound execution.

`agent/planner.py`, `agent/memory.py`, older `rag/`/pipeline abstractions and
`interfaces.py` include scaffold/reserved code; their existence is not evidence
of layered memory, separate planning, production ACLs or zero-cost backend swaps.
Current code still depends directly on SQLite repositories and Ollama settings
in places. Stronger interface boundaries require a future refactoring module.

## Background jobs

Web submission → `POST /api/jobs` (202) → SQLite jobs → lifespan worker → shared
chat-model lock → Agent loop → persisted results/events → Web two-second polling.
The worker is not owned by an HTTP/SSE request. Leaving the page stops polling,
not execution. Jobs waiting for the model lock remain queued. Queued cancellation
is immediate; running cancellation stops its child task and records a terminal
state even when cancellation arrives before the child's first scheduled step.

On startup queued jobs resume and abandoned running/cancelling jobs become
interrupted. Explicit retry creates a new linked job; no blind replay. The
computer and backend process must remain running: there is no login item,
system daemon, distributed queue or high-availability deployment. Run only one
backend worker/instance per database. See [background-jobs-design.md](background-jobs-design.md).

## Confirmed AI terminal V3

New tasks use `terminal/plans.py`: the model generates actual exec program/arguments
or a full shell script, not a functional action enum. The backend resolves programs,
binds directory/executable identity and exact content to an immutable plan hash. Scripts
run via a fixed bash launcher with no initialization files and pipefail; exec avoids shell.

All plans require explicit current-account/no-sandbox acknowledgement. The console's
`y` answer is one explicit confirmation carrying the account/high-risk/network records
for the plan shown on screen; potential code/file effects and network access are listed
before it is accepted. Warnings are heuristic, not an isolation boundary: arbitrary
commands can access the user's files/network beyond their initial cwd. No sudo/password
or interactive PTY is provided.
Each step is bounded to 300 seconds/128KiB; process-group cleanup, cancel and restart records
remain. Failed commands are not repaired/rerun without a new plan and confirmation.

`GET /api/terminal/transcript` returns recent tasks in chronological order for the
single console scrollback; the page no longer needs a separate list/detail selection.
Planning prepends a bounded summary (≤6 finished exchanges: request, commands, exit codes,
truncated output) marked as untrusted data so follow-ups have context; it cannot reuse
an earlier approval or inject instructions. Free text in the input box is always planned
by the model, never executed as a literal shell line.

Legacy catalog records remain readable; new plans never depend on those action enums.
Recognized exact local lsof results retain structured port facts. Sysctl physical-memory
output has deterministic GiB/GB formatting; other summaries remain model interpretations.
See [generative-terminal-design.md](generative-terminal-design.md).

## SQLite records

- `documents` / `chunks` / FTS5: uploaded metadata, chunk text and keyword index.
- `conversations` / `messages`: history, reply state and source citations.
- `runs` / `run_events`: durable model/tool action records.
- `jobs`: instructions, diagnostic scope, status, timestamps, result, error and
  related conversation/run/retry parent. Linked conversations cannot be deleted
  via the ordinary chat endpoint. Task deletion is not implemented.

## Offline and capability boundary

Dependencies and weights are downloaded separately while online. Runtime model
calls ignore environment proxies, reject non-loopback endpoints and cloud model
stubs. The UI bundles assets locally and does not execute model HTML or load
remote images. There are no cloud inference APIs, enterprise resources, telemetry
or contribution collectors in the project.

Diagnostic adapters use public, fixed read-only code, no shell or sudo; port
lookup is limited to current-user-visible TCP listeners. Machine results and
private imported documents stay in ignored local data, never repository fixtures.
The confirmed terminal is the exception to read-only job tools: it can execute reviewed
commands/scripts, modify files and access network if authorized. No GUI/browser automation,
tenant authentication/isolation or enterprise compliance certification is provided. Basic
Host/Origin checks and risk confirmations are not OS/file/network isolation.
