# Roadmap

## Current workbench and reliability follow-up
- [x] Single sidebar, central chat/terminal and right question/context inspector.
- [x] Terminal rename/delete and current-view question anchors.
- [x] Fix observed history overflow/menu wrapping and preserve context visibility.
- [x] Add limited exact decimal / ASCII letter verification and local evaluation entry.
- [x] Document evolution, encountered problems, rejected experiments and current boundaries.
- [ ] Strict answer/reason evaluation with versioned public outputs; replace keyword screening.
- [ ] Compare local models on held-out traps and opposing control questions.
- [ ] Restart and end-to-end verify latest reasoning backend path.
- [ ] Full-history terminal directory, accessibility and cross-browser/mobile regression matrix.
- [ ] Clean-machine installation, license/security review and versioned open-source release.

The phase sections below describe historical delivery milestones, not one combined security scope.

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
- [x] Immutable catalog plans, directory checks and explicit hash-bound confirmation.
- [x] Persistent execution/output, cancellation, expiry and restart interruption.
- [x] Natural-language terminal UI, plan review and separate facts/model summary.
- [x] Real local model/command acceptance and regression tests.
- [x] Confirmed local TCP port query, persisted facts and backend-owned error messages.

## Phase 8 — Generated terminal V3
- [x] Actual exec/program/args and full shell plans rather than a functional action enum.
- [x] Hash-bound account/high-risk/network confirmation records and backend validation.
- [x] Real model memory query, synthetic development test and shell redirection acceptance.
- [x] Separate facts/explanation, deterministic memory unit formatting and bounded execution.
- [x] Console UI: terminal window, single scrollback transcript, bottom `❯` dialogue input
  with `y`/`n` confirmation, `↑`/`↓` input history and bounded follow-up context.
- [ ] PTY/password interaction, OS/file/network isolation and long-running service management.

## Phase 5 — Agent & extensions
- [x] Tool registration and bounded model → tool → observation loop.
- [x] Durable execution records, source cards and inspection UI.
- [ ] Layered memory (short-term / long-term).
- [ ] Optional: code-specialized model, multimodal, desktop shell.
