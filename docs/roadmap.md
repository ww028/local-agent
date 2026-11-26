# Roadmap

## Phase 0 — Environment scaffold
- [x] Repository layout, MIT license, ignore rules, example env.
- [x] FastAPI skeleton with health check and pluggable interfaces.
- [x] React + Vite skeleton with chat and documents pages.

## Phase 1 — Chat loop
- [x] Wire Ollama chat streaming, cancellation and errors end to end (fake-model tests).
- [x] Installed model discovery, local capability checks and UI selection.
- [x] Conversation persistence, restore and delete in SQLite.
- [x] Real Ollama inference, short-sample performance and browser chat/cancel/history acceptance.
- [ ] Physical network-disconnect acceptance and long-context/peak-memory profiling.

## Phase 2 — Ingestion pipeline
- [x] Markdown parse → structural chunk → embed → LanceDB index.
- [x] Document list / delete / reindex in the UI.
- [ ] Reserved PDF / Word parser interfaces.

## Phase 3 — RAG QA
- [x] Hybrid retrieval (semantic + keyword), Top-K, citation payload.
- [x] Grounded prompt composition with source citations.
- [x] Citation cards linking back to the source chunk.

## Phase 4 — Experience
- [x] Multi-session management, history view, rename/export.
- [x] Markdown rendering.
- [x] Code syntax highlighting / math rendering.
- [x] Standalone execution history page and packaged local web startup.
- [x] Synthetic 151K-character document indexing and exact recall smoke test.
- [x] Temperature and mode controls.
- [ ] Per-turn output-token/Top-K tuning.

## Phase 6 — Background task center
- [x] Persisted jobs, request-independent execution and bounded queue.
- [x] Status/results UI with cancel/retry and restart interruption handling.
- [x] Explicit opt-in local TCP port/system read-only diagnostics.
- [x] Real model job + browser-refresh acceptance and regression tests.

## Phase 7 — Confirmed AI terminal
- [ ] Immutable catalog plans, directory checks and explicit hash-bound confirmation.
- [ ] Persistent execution/output, cancellation, expiry and restart interruption.
- [ ] Natural-language terminal UI, plan review and separate facts/model summary.
- [ ] Real local model/command acceptance and regression tests.

## Phase 5 — Agent & extensions
- [x] Tool registration and bounded model → tool → observation loop.
- [x] Durable execution records, source cards and inspection UI.
- [ ] Layered memory (short-term / long-term).
- [ ] Optional: code-specialized model, multimodal, desktop shell.
