# Phase 1 acceptance

Implemented: local model discovery and next-message selection; streaming chat;
stop-generation UI; durable SQLite conversation history; partial/error states;
conservative context budgeting; single-generation concurrency guard; Markdown
rendering without remote images; root configuration and public package sources.

## Validation performed

- 22 backend tests passed: chat sequence, multi-turn history, persistence across
  app restarts, deletion, failed/partial output, cancellation, busy rejection,
  validation, local-only configuration, model capability checks and old-DB migration.
- 5 frontend SSE tests passed: UTF-8 byte splitting, CRLF frames, error terminal,
  unexpected EOF and malformed JSON.
- Ruff and TypeScript checks passed; Vite production build passed.
- `npm ci` from the public registry succeeded; npm audit reported 0 known
  vulnerabilities at test time. This is not a guarantee of security.
- HTTP startup smoke test passed for backend health, frontend HTML, proxy,
  alternate ports, and cross-origin rejection. Spawned test servers were stopped.
- Public-source guard and manual repository text scan passed. No models, runtime
  database, private documents, corporate dependencies or telemetry config added.

## Real local-model acceptance

- Official Ollama was installed and its archive checksum, code signature and
  macOS notarization were verified. Cloud is disabled and the server listens
  only on 127.0.0.1:11434; no login/autostart was configured.
- `qwen3:14b` Q4_K_M finished downloading and digest verification succeeded.
- At an 8192-token context setting, a short Chinese prompt generated 93 output
  tokens. First run: first token 5.533 s, model load 5.023 s, total 8.984 s,
  decode 26.94 tokens/s. Second run: first token 0.048 s, total 3.564 s,
  decode 26.46 tokens/s. The repeated prompt benefits from a warm/cache state;
  these are short smoke-test measurements, not a sustained benchmark.
- Ollama `/api/ps` reported 10,332,122,643 bytes of model allocation, all assigned
  to GPU. This is not a whole-system or peak-resident-memory measurement.
- Real workbench API multi-turn history and fictional fact recall passed.
- Browser UI: model refresh, Chinese chat, follow-up recall, page reload and
  reopening history, stopping a long answer, partial/interrupted display and
  starting another answer all passed.
- Whole-system swap was approximately 13 GB during testing. No pre-inference
  baseline was recorded, so it cannot be attributed to Ollama alone.

## Still unverified / not delivered

- Physical network-disconnect acceptance, broad answer-quality evaluation,
  long-context stress tests and accurate peak-memory profiling.
- Switching between two distinct installed models (only one model installed).
- Knowledge ingestion, retrieval, tool calling, enterprise authentication and
  multi-user/production serving are subsequent phases, not current features.
- One upstream Starlette TestClient deprecation warning remains; tests pass.
- Browser diagnostics included an earlier disconnect and a blocked blob worker;
  current chat interactions succeeded. No full browser compatibility audit claimed.

## Manual acceptance after installing a local runtime

1. Start Ollama with cloud features disabled; install one local chat model.
2. Run `bash scripts/dev.sh` and open `http://127.0.0.1:5173`.
3. Refresh models; select one and send a short message.
4. Ask a follow-up; reload the page, reopen the conversation and verify history.
5. Stop a long reply; verify interrupted state and that another reply can start.
6. Switch models for the next message; verify the saved model label.
7. Stop Ollama and verify a visible error, not a permanently disabled composer.
8. Disconnect network and repeat local chat with already downloaded weights.

See [setup.md](setup.md) for installation and offline boundaries.
