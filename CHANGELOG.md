# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Confirmation is now decided by effects, not by a tool whitelist: a "look at something"
  request (查看/看看/查询/列出/是什么/多少/版本/状态…) executes directly unless any step can
  write, delete, install, change settings or reach the network (`writes_anything()`), in which
  case it still asks. `observation` plans are audited as `{"auto_observe": true}` and are
  re-verified before launch. This ends the "one tool, one whitelist entry" treadmill.
- Version questions no longer depend on a fixed tool table: the single tool name in the
  sentence that actually resolves on the machine is used (`python`→`python3`, `pip`→`pip3`,
  `nodejs`→`node`), so "我的python 版本呢？" answers "Python 版本：3.9.6" without a click.
- Read-only shell scripts now run without confirmation as a matter of principle rather than a
  per-tool whitelist: `read_only_script()` strips allowed redirects, rejects command
  substitution, pipes, chaining and any mutating segment, then proves every segment starts
  from a trusted absolute program with read-only arguments. Pure-read pipelines such as
  `ls <dirs> | grep -Ei '...'`, `which a; which b`, `find` and `2>/dev/null` therefore skip the
  approval card, while anything that could write, install or reach the network still asks.
- Read-only steps that exit non-zero (grep/find/lsof "no match") no longer count as failures,
  and an all-no-match plan reports "没有找到匹配项" instead of a red error line.
- BSD `grep` alternation is normalised (`grep -i 'a\|b'` -> `grep -Ei 'a|b'`).
- "What software/databases are installed" plans have their `ls <dirs>` scope completed with the
  real install dirs from PATH (e.g. Homebrew's `/opt/homebrew/bin`), so MySQL is found instead
  of reported missing.
- Read-only terminal queries run without a confirmation click: only provable read-only
  `exec` invocations (known system programs with whitelisted arguments) are auto-approved and
  audited as `{"auto_readonly": true}`; shell, scripts, unknown programs and anything that may
  write files, change settings, install software or use the network still require confirmation.
- The confirmation card now states consequences in plain language (read-only / may write or
  overwrite files / may delete files / may install software / may change system settings / may
  reach the network) and folds the command text under "查看即将执行的命令".
- Terminal replies lead with a deterministic result line (architecture, RAM in GiB, CPU model,
  macOS version, git branch/clean state) taken from real stdout; the model explanation is a
  short supplement, and raw output plus the command stay folded.

### Fixed
- "X 版本号" requests use a deterministic read-only path: the tool is resolved against the
  user's own toolchains (nvm default version, Volta, ~/.local/bin, ~/.cargo/bin) instead of
  asking the model to `which` it, so `node --version` answers instantly without a click.
- A failed step now reports the command name, exit code and first stderr line instead of a
  generic "命令退出码非零", so the console says why nothing was executed.
- CPU-model requests no longer answer with `uname -m` (architecture): the plan is normalized to
  `sysctl -n machdep.cpu.brand_string`.
- The console keeps following new output when the tab is in the background, where
  `requestAnimationFrame` is paused (timers plus ResizeObserver now drive the scroll).
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
