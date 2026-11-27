# Contributing to local-agent

Thanks for your interest! This project is local-first and open source under the MIT License.

## Ground rules

- Keep the runtime **offline-capable**: no hard dependency on cloud APIs, telemetry or
  third-party hosted services. Optional features must be opt-in.
- No private documents, credentials, internal hosts or personal data may be committed.
- All third-party dependencies and assets must be permitted for use in an MIT-licensed project.

## Development setup

See [docs/setup.md](docs/setup.md). In short:

1. Fork and clone the repository.
2. Create a feature branch from `main`.
3. Install backend and frontend dependencies.
4. Make your change, add/adjust tests, and run lint + tests locally.
5. Open a pull request describing the change and its rationale.

## Code conventions

- **Backend**: type-annotated Python; keep business logic out of route handlers; depend on
  interfaces, not concrete implementations.
- **Frontend**: TypeScript; keep components presentational, API calls isolated in `src/api`.
- **Pluggable points**: new document parsers, retrieval strategies, tools and model backends
  should implement the existing interfaces under `backend/app/interfaces.py`.

## Adding a tool

Tools live in `backend/app/agent/tools/`. Implement the tool interface, register it in the
agent executor, and document its inputs/outputs in the tool module docstring.

## Documentation is part of the change

Read [docs/README.md](docs/README.md). Record reproducible problems, evidence, chosen/rejected
approaches, implementation references, tests and remaining risks in the issue/decision log.
Update current architecture and README when capability changes; keep superseded designs clearly
marked historical. Record failed experiments as well as successful ones. Never present keyword
matches, mock tests or one machine's results as general accuracy, performance or security proof.
Use public/synthetic examples; do not commit runtime databases, private inputs or hidden thinking.

## Reporting issues

Use the issue templates under `.github/ISSUE_TEMPLATE/`. Include environment (OS, Python/Node
version, models used) and steps to reproduce.
