"""Chat endpoints, including SSE streaming."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.schemas import ChatRequest

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.post("/stream")
async def stream_chat(request: Request, body: ChatRequest) -> StreamingResponse:
    service = request.app.state.rag_service

    async def event_stream():
        async for event in service.answer(body):
            yield f"data: {json.dumps(event.model_dump(exclude_none=True))}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
