# Setup

## Prerequisites

- **Python 3.11–3.13** (3.14 is very new; some dependencies may not have wheels
  yet, so a 3.11–3.13 virtualenv is recommended).
- **Node 20+** and npm.
- **Ollama** installed and running (<http://localhost:11434>).

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Check health: <http://localhost:8000/health>

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the printed URL (default <http://localhost:5173>). Vite proxies `/api` to
the backend on port 8000.

## Models

Pull the local models (see [models.md](models.md) for options):

```bash
ollama pull qwen3:14b
ollama pull bge-m3
```

## Configuration

Copy `.env.example` to `.env` and adjust model names, ports, paths and RAG
tuning. `.env` and `data/` are gitignored.

## Tests

```bash
cd backend
pytest
```
