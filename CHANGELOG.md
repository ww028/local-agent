# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project scaffold: FastAPI backend, React + Vite frontend, LanceDB + SQLite storage layer.
- Pluggable interfaces for model backend, vector store and repositories.
- Markdown parser/chunker prototypes and ingestion interfaces (not a working RAG pipeline).
- Agent skeleton: planner, tools, memory, executor (execution pending).
- Phase 1 local SSE chat with installed-model selection and SQLite history.
- Cancellation, partial/error states, conservative context budget and local-only guards.
- Fake-model API/adapter tests and frontend SSE regression tests.
