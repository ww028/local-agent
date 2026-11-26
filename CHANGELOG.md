# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Persistent background task center with service-owned worker, durable queue/results/events,
  explicit cancellation/retry and restart interruption handling independent of browser lifetime.
- Per-job opt-in read-only TCP listener/system diagnostics with fixed commands, time/output
  bounds and subprocess cleanup; no arbitrary shell, GUI control or process termination.
- Task result UI with two-second status polling, collapsed tool facts and persisted knowledge
  citations; regression coverage for immediate cancellation and required tools after retrieval.
- Project scaffold: FastAPI backend, React + Vite frontend, LanceDB + SQLite storage layer.
- Pluggable interfaces for model backend, vector store and repositories.
- Markdown indexing queue, local embeddings, LanceDB/FTS5 hybrid retrieval and persisted citations.
- Bounded model-driven Agent loop with safe calculator, local search/read tools and durable events.
- Knowledge library upload/status/reindex/preview/delete UI.
- Session rename/search/export, restored selection, execution inspection and temperature/mode controls.
- Phase 1 local SSE chat with installed-model selection and SQLite history.
- Cancellation, partial/error states, conservative context budget and local-only guards.
- Fake-model API/adapter tests and frontend SSE regression tests.
