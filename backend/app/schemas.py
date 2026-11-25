"""Shared Pydantic models for API requests/responses and internal records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    # Optional tool-call metadata, populated by the agent layer.
    tool_calls: list[dict] | None = None


class Citation(BaseModel):
    document_id: str
    document_title: str
    chunk_id: str
    heading: str | None = None
    snippet: str


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    heading: str | None = None
    text: str
    score: float = 0.0


class DocumentMeta(BaseModel):
    document_id: str
    title: str
    source_path: str | None = None
    chunk_count: int = 0
    # Reserved for future multi-tenant / ACL support. Local build treats as public.
    owner_id: str | None = None
    tenant_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    conversation_id: str | None = None
    use_knowledge_base: bool = False
    mode: Literal["chat", "knowledge", "agent"] = "chat"
    model: str | None = Field(default=None, max_length=200)
    top_k: int | None = Field(default=None, ge=1, le=20)


class ChatStreamEvent(BaseModel):
    type: Literal["meta", "token", "citation", "step", "done", "error"]
    run_id: str | None = None
    event: dict | None = None
    conversation_id: str | None = None
    message_id: int | None = None
    model: str | None = None
    content: str | None = None
    citations: list[Citation] | None = None
    error: str | None = None
