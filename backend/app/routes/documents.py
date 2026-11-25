"""Local document management. IDs are UUIDs, never user filesystem paths."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

router = APIRouter(tags=["knowledge"])


def service(request):
    return request.app.state.knowledge


def valid(key):
    import re

    if not re.fullmatch(r"[a-f0-9]{32}", key):
        raise HTTPException(404, "Document not found")


@router.get("/api/documents")
async def list_documents(request: Request):
    return {"documents": service(request).repo.list_all()}


@router.post("/api/documents")
async def ingest_document(request: Request, file: Annotated[UploadFile, File()]):
    data = await file.read(4 * 1024 * 1024 + 1)
    try:
        return await service(request).ingest(file.filename or "document.md", data)
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/api/documents/{key}")
async def preview(key: str, request: Request):
    valid(key)
    try:
        return service(request).preview(key)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(404, "Document not found") from exc


@router.post("/api/documents/{key}/reindex")
async def reindex(key: str, request: Request):
    valid(key)
    try:
        await service(request).reindex(key)
        return {"queued": key}
    except KeyError as exc:
        raise HTTPException(404, "Document not found") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.delete("/api/documents/{key}")
async def delete(key: str, request: Request):
    valid(key)
    try:
        await service(request).delete(key)
        return {"deleted": key}
    except KeyError as exc:
        raise HTTPException(404, "Document not found") from exc


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=12)


@router.post("/api/knowledge/search")
async def search(request: Request, body: SearchRequest):
    try:
        return {"chunks": await service(request).search(body.query, body.top_k)}
    except Exception as exc:
        raise HTTPException(503, "Local search unavailable; check embedding model") from exc
