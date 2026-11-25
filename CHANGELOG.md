# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project scaffold: FastAPI backend, React + Vite frontend, LanceDB + SQLite storage layer.
- Pluggable interfaces for model backend, vector store and repositories.
- RAG ingestion pipeline (Markdown parse → structural chunk → embed → index).
- Agent skeleton: planner, tools, memory, executor.
