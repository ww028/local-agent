"""Document ingestion and knowledge-base management."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
def list_documents(request: Request) -> dict:
    repo = request.app.state.document_repo
    return {"documents": repo.list_all()}


@router.post("")
async def ingest_document(request: Request, file: UploadFile = File(...)) -> dict:
    pipeline = request.app.state.ingest_pipeline
    content = (await file.read()).decode("utf-8", errors="replace")
    if not content.strip():
        raise HTTPException(status_code=400, detail="Empty document.")
    document_id = await pipeline.ingest_markdown(content, source_name=file.filename or "document.md")
    return {"document_id": document_id}


@router.delete("/{document_id}")
def delete_document(request: Request, document_id: str) -> dict:
    repo = request.app.state.document_repo
    repo.delete(document_id)
    # TODO: await store.delete_document(document_id) once vector deletion lands.
    return {"deleted": document_id}
