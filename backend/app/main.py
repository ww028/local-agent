"""App factory. Importing the module does not create files or open a database."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import Settings, get_settings
from app.ollama_client import OllamaChatModel
from app.routes import chats, models
from app.store.chats import ChatRepository
from app.store.db import get_connection


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
        try:
            yield
        finally:
            conn.close()

    app = FastAPI(title="local-agent", version="0.1.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None)  # Avoid documentation UI CDN dependencies.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])

    @app.middleware("http")
    async def local_origin(request: Request, call_next):
        # Loopback is not authentication. Reject cross-site browser requests;
        # trusted CLI clients without Origin remain allowed in single-user mode.
        origin = request.headers.get("origin")
        allowed = {f"http://localhost:{config.frontend_port}",
                   f"http://127.0.0.1:{config.frontend_port}",
                   f"http://localhost:{config.backend_port}",
                   f"http://127.0.0.1:{config.backend_port}"}
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

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "phase": 1, "knowledge_base": False}

    @app.api_route("/api/documents", methods=["GET", "POST", "DELETE"])
    @app.api_route("/api/documents/{key}", methods=["DELETE"])
    async def documents_unavailable():
        raise HTTPException(501, "Document ingestion is scheduled for phase 2.")

    return app


app = create_app()
