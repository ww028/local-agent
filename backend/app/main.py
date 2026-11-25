"""FastAPI application entrypoint and dependency wiring.

Concrete implementations are bound here; the workflow layers depend on the
interfaces, so backends and stores can be swapped in one place.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.ingest.pipeline import IngestPipeline
from app.ollama_client import OllamaChatModel, OllamaEmbeddingModel
from app.rag.retriever import Retriever
from app.rag.service import RagService
from app.routes import chats, documents, models
from app.store.chats import ChatRepository
from app.store.db import get_connection
from app.store.documents import DocumentRepository
from app.store.vector_store import LanceDBStore

settings = get_settings()
settings.ensure_dirs()

app = FastAPI(title="local-agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{settings.frontend_port}", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Wiring (concrete implementations) ---
chat_model = OllamaChatModel(settings)
embedding_model = OllamaEmbeddingModel(settings)
vector_store = LanceDBStore(settings)
retriever = Retriever(embedding_model, vector_store)
rag_service = RagService(settings, chat_model, retriever)

conn = get_connection(settings)
document_repo = DocumentRepository(conn)
chat_repo = ChatRepository(conn)
ingest_pipeline = IngestPipeline(settings, embedding_model, vector_store)

app.state.settings = settings
app.state.chat_model = chat_model
app.state.embedding_model = embedding_model
app.state.vector_store = vector_store
app.state.rag_service = rag_service
app.state.document_repo = document_repo
app.state.chat_repo = chat_repo
app.state.ingest_pipeline = ingest_pipeline

app.include_router(models.router)
app.include_router(documents.router)
app.include_router(chats.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm_model": settings.llm_model, "embedding_model": settings.embedding_model}
