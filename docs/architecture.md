# Architecture

local-agent is a local-first workbench split into decoupled layers. The workflow
code depends on interfaces, not concrete implementations, so a backend or store
can be swapped without rewriting the RAG or agent logic.

## Layers

```
┌──────────────────────────────────────────────────────────┐
│ Frontend (React + Vite) — chat UI, knowledge base, citations │
├──────────────────────────────────────────────────────────┤
│ Backend (FastAPI)                                          │
│  ├─ routes/      HTTP handlers, SSE streaming               │
│  ├─ rag/         retrieval, prompt composition, QA service│
│  ├─ ingest/      parse → chunk → embed → index              │
│  ├─ agent/       planner, tools, memory, executor loop     │
│  └─ store/       SQLite business records, LanceDB index   │
├──────────────────────────────────────────────────────────┤
│ Interfaces (app/interfaces.py)                             │
│  ChatModel · EmbeddingModel · VectorStore                 │
├──────────────────────────────────────────────────────────┤
│ Local runtime: Ollama (chat + embedding models)            │
└──────────────────────────────────────────────────────────┘
```

## Pluggable interfaces

| Interface      | Default implementation | Future replacement example |
| -------------- | ---------------------- | -------------------------- |
| `ChatModel`    | `OllamaChatModel`      | vLLM / TGI / hosted API    |
| `EmbeddingModel` | `OllamaEmbeddingModel` | TEI / sentence-transformers |
| `VectorStore`  | `LanceDBStore`         | Qdrant / Milvus / Weaviate  |

## RAG data flow

1. **Ingest**: Markdown (frontmatter + body) → heading-aware chunks with overlap.
2. **Embed**: local embedding model turns each chunk into a vector.
3. **Index**: vectors + chunk metadata written to LanceDB; document and chunk
   records written to SQLite.
4. **Retrieve**: query is embedded, hybrid retrieval returns Top-K chunks,
   optionally scoped to accessible document IDs (reserved for ACL use).
5. **Answer**: chunks are composed into the prompt with sources; the chat model
   streams a grounded answer; citations are returned to the frontend.

## Agent layer

- `planner`: break a goal into steps.
- `tools/`: callable capabilities (knowledge search is the first tool).
- `memory`: short-term conversation history separate from long-term facts.
- `executor`: think → act → observe loop, registering and invoking tools.

## Data model (SQLite)

- `documents`: metadata, reserved `owner_id` / `tenant_id` for future ACL.
- `chunks`: chunk text, heading, order, parent document.
- `conversations` / `messages`: chat history.

Vectors live in LanceDB; business records live in SQLite. The two are linked by
document / chunk IDs.

## Background jobs (planned implementation in this batch)

A persisted `jobs` queue is serviced by a lifespan-owned worker, independent of
HTTP/SSE request lifetime. Job execution shares the existing model lock, produces
run events and durable final results. Queued work resumes on startup; previously
running work is marked interrupted, never blindly replayed. Optional per-job
read-only diagnostics are a separate capability, not arbitrary shell access.
See [background-jobs-design.md](background-jobs-design.md).

## Offline boundary

At runtime everything talks to `localhost`: no cloud LLM, no hosted embedding
service, no remote vector database. Models and packages are downloaded once while
online, then used offline.
