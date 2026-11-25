"""Model listing and selection."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
def list_models(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "llm": settings.llm_model,
        "embedding": settings.embedding_model,
    }
