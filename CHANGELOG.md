# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Terminal console readability: requests and AI replies render as dialogue bubbles inside
  the terminal window; the pending decision is an amber "需要你确认才执行" card with large
  `执行 (y)` / `取消 (n)` buttons plus a hint bar above the input. Decorative traffic-light
  dots were removed because they were non-functional.
- The console now auto-scrolls to the newest content (new request, generated plan, streamed
  output, approval state); following pauses only while you scroll up and resumes at the bottom.

### Fixed
- AI terminal now plans/executes confirmed local TCP port diagnostics with strict integer
  targets and persisted facts; local lookup does not need networking. Shared lsof result
  parsing distinguishes no visible listener from permission/warning/timeout failure.
- Unsupported planning errors are backend-owned rather than unverified model explanations;
  target mismatch never executes another port, existing approval bindings remain mandatory.

### Added
- Generated terminal V3: model-generated actual exec/argv or full shell script plans instead
  of a fixed functional catalog. Exact plan review, account/high-risk/network acknowledgements
  persist before execution. No OS sandbox or network isolation is implied.
- Direct system/development commands and reviewed shell pipelines/redirection, bounded
  runtime/output, no shell initialization, pipefail and deterministic memory-unit formatting.
- Terminal console UI: macOS-style window with one chronological scrollback and a bottom
  dialogue input; `y`/`n` confirms a pending plan in conversation, `↑`/`↓` recalls input
  history, and bounded recent transcript context supports follow-up questions.
- `GET /api/terminal/transcript` for the console scrollback; free text is always model-planned,
  never executed as a literal shell line.
- Confirmed AI terminal: local-model planning into a fixed read-only catalog, immutable
  hash-bound ten-minute approval, backend execution and separate output/model explanation.
- Project-directory/Git-status/diff-stat/recent-log/version actions, bounded stdout/stderr,
  exit codes, cancellation, process-group cleanup and restart interruption; no arbitrary shell.
- Terminal plan review/history/replan UI, confirmation idempotency and security regressions.
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
