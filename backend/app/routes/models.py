"""Discover installed models without automatically pulling weights."""

from fastapi import APIRouter, Request

from app.ollama_client import ModelError

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
async def list_models(request: Request) -> dict:
    state = request.app.state
    try:
        installed = await state.chat_model.list_models()
        return {
            "llm": state.settings.llm_model,
            "embedding": state.settings.embedding_model,
            "available": [
                m for m in installed if "completion" in m.get("capabilities", ["completion"])
            ],
            "status": "ready",
        }
    except ModelError as exc:
        return {
            "llm": state.settings.llm_model,
            "embedding": state.settings.embedding_model,
            "available": [],
            "status": "unavailable",
            "error": str(exc),
        }
