# Roadmap

## Phase 0 — Environment scaffold
- [x] Repository layout, MIT license, ignore rules, example env.
- [x] FastAPI skeleton with health check and pluggable interfaces.
- [x] React + Vite skeleton with chat and documents pages.

## Phase 1 — Chat loop
- [ ] Wire Ollama chat streaming end to end.
- [ ] Model selection endpoint and UI control.
- [ ] Conversation persistence in SQLite.

## Phase 2 — Ingestion pipeline
- [ ] Markdown parse → structural chunk → embed → LanceDB index.
- [ ] Document list / delete / reindex in the UI.
- [ ] Reserved PDF / Word parser interfaces.

## Phase 3 — RAG QA
- [ ] Hybrid retrieval (semantic + keyword), Top-K, citation payload.
- [ ] Grounded prompt composition with source citations.
- [ ] Citation cards linking back to the source chunk.

## Phase 4 — Experience
- [ ] Multi-session management, history view.
- [ ] Markdown rendering and code highlighting.
- [ ] Tuning controls (temperature, Top-K, knowledge-base toggle).

## Phase 5 — Agent & extensions
- [ ] Tool registration and think → act → observe loop.
- [ ] Layered memory (short-term / long-term).
- [ ] Optional: code-specialized model, multimodal, desktop shell.
