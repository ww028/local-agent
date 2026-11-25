"""App factory. Importing the module does not create files or open a database."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.agent.executor import Executor
from app.agent.toolbox import Tools
from app.config import Settings, get_settings
from app.knowledge import KnowledgeService
from app.ollama_client import OllamaChatModel, OllamaEmbeddingModel
from app.routes import chats, documents, models
from app.store.chats import ChatRepository
from app.store.db import get_connection
from app.store.documents import DocumentRepository
from app.store.runs import RunRepository
from app.store.vector_store import LanceDBStore


def create_app(settings: Settings | None = None, chat_model=None) -> FastAPI:
    config = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        conn = get_connection(config)
        app.state.settings = config
        app.state.chat_repo = ChatRepository(conn)
        app.state.chat_model = chat_model or OllamaChatModel(config)
        app.state.chat_lock = asyncio.Lock()
        app.state.active_conversation = None
        app.state.knowledge = KnowledgeService(
            config, DocumentRepository(conn), LanceDBStore(config), OllamaEmbeddingModel(config)
        )
        await app.state.knowledge.start()
        app.state.runs = RunRepository(conn)
        app.state.agent = Executor(app.state.chat_model, Tools(app.state.knowledge), app.state.runs)
        try:
            yield
        finally:
            await app.state.knowledge.stop()
            conn.close()

    app = FastAPI(
        title="local-agent", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None
    )  # Avoid documentation UI CDN dependencies.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])

    @app.middleware("http")
    async def local_origin(request: Request, call_next):
        # Loopback is not authentication. Reject cross-site browser requests;
        # trusted CLI clients without Origin remain allowed in single-user mode.
        origin = request.headers.get("origin")
        allowed = {
            f"http://localhost:{config.frontend_port}",
            f"http://127.0.0.1:{config.frontend_port}",
            f"http://localhost:{config.backend_port}",
            f"http://127.0.0.1:{config.backend_port}",
        }
        if origin and origin not in allowed:
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "Cross-origin requests are blocked."}, status_code=403)
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.include_router(models.router)
    app.include_router(chats.router)
    app.include_router(documents.router)

    @app.get("/api/runs/{key}")
    async def run_detail(key: str, request: Request):
        from fastapi import HTTPException

        result = request.app.state.runs.get(key)
        if not result:
            raise HTTPException(404, "Run not found")
        return result

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "phase": 2, "knowledge_base": True}

    return app


app = create_app()
