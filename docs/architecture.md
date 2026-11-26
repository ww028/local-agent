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

## Confirmed AI terminal (planned in this batch)

A separate persisted terminal task moves from model planning to awaiting confirmation.
A backend-owned command catalog creates immutable executable/argv/cwd plans; a hash
binds the user's confirmation to the exact version. A separate command worker executes
only approved catalog steps with bounded output/time and no shell. Model planning and
summary share the existing model lock; waiting for approval does not hold it. No arbitrary
commands, scripts, network or writes in the initial scope. See [ai-terminal-design.md](ai-terminal-design.md).

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
No arbitrary commands, file writes, process termination, network search,
GUI/browser automation, authentication/tenant isolation or enterprise compliance
certification are implemented. Basic Host/Origin checks are not a full sandbox.
