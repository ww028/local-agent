# local-agent

A **local-first, privacy-first** open-source Agent workbench. Run LLMs, embeddings and
knowledge retrieval entirely on your own machine; your documents never leave localhost.

> Status: **phase 1 implemented**: local streaming chat, model selection and durable
> conversation history. RAG and Agent execution are not yet implemented — see [Roadmap](docs/roadmap.md).

## Why local-agent

- **Fully offline** at runtime: models, embeddings and vector index run locally via [Ollama](https://ollama.com).
- **Local streaming chat**: model switching, stop generation, Markdown output and SQLite history.
- **RAG roadmap**: Markdown knowledge base → chunk → embed → hybrid retrieval → cited answers (planned).
- **Agent architecture scaffold**: tool definitions and memory interfaces exist; execution is not implemented.
- **Pluggable internals**: model backend, vector store and repositories sit behind interfaces,
  so implementations can be swapped without touching the workflow layer.

## Tech stack

| Layer        | Choice                                             |
| ------------ | -------------------------------------------------- |
| Backend      | Python · FastAPI · Uvicorn · Pydantic             |
| Frontend     | React · Vite · TypeScript                          |
| Model runtime| Ollama (chat model + embedding model)              |
| Vector store | LanceDB (semantic + keyword hybrid retrieval)      |
| Business DB  | SQLite (documents, chunk state, chat history)      |

## Quick start

Prerequisites: **Python 3.11–3.14**, **Node 20.19+ / 22.12+**, **local Ollama** installed and running.

```bash
# 1. Clone and enter
git clone https://github.com/ww028/local-agent.git
cd local-agent

# 2. Configure
cp .env.example .env

# 3. Install dependencies (does not download weights)
bash scripts/setup.sh
# Separately start local Ollama and download a chat model while online.
# Embeddings are not needed until phase 2.

# 4. Run backend and frontend in one terminal
bash scripts/dev.sh
```

Then open the printed frontend URL (default <http://localhost:5173>).

## Repository layout

```
local-agent/
├── backend/          # FastAPI service: ingest, RAG, agent, store, routes
├── frontend/         # React + Vite workbench UI
├── docs/             # Architecture, setup, model notes, roadmap
├── examples/         # Sample Markdown knowledge base (fictional)
├── scripts/          # Setup, model pull, dev launcher
└── .github/          # CI and contribution templates
```

See [docs/architecture.md](docs/architecture.md) for the layered design and
[docs/setup.md](docs/setup.md) for detailed environment setup.

## Models and licensing

Code in this repository is released under the **MIT License** (see [LICENSE](LICENSE)).
Model weights are **not** bundled; you pull them through Ollama under each model's own
license. Review the terms of the chat and embedding models you use — some impose
attribution or commercial-use restrictions. See [docs/models.md](docs/models.md).

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening
an issue or pull request.

## License

[MIT](LICENSE) © local-agent contributors
