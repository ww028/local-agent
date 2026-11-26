"""Request-independent background jobs API."""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=2000)
    model: str | None = Field(default=None, max_length=200)
    allow_diagnostics: bool = False

    @field_validator("instruction")
    @classmethod
    def nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Task instruction must not be blank")
        return value


@router.post("", status_code=202)
async def submit(request: Request, body: JobRequest):
    try:
        return request.app.state.jobs.submit(
            body.instruction,
            body.model or request.app.state.settings.llm_model,
            body.allow_diagnostics,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("")
async def list_jobs(
    request: Request, limit: int = Query(50, ge=1, le=50), offset: int = Query(0, ge=0)
):
    return {"jobs": request.app.state.jobs.repo.list(limit, offset)}


@router.get("/{key}")
async def get_job(key: str, request: Request):
    job = request.app.state.jobs.repo.get(key)
    if job is None:
        raise HTTPException(404, "Task not found")
    if job["run_id"]:
        run = request.app.state.runs.get(job["run_id"])
        job["events"] = run["events"] if run else []
    else:
        job["events"] = []
    job["citations"] = []
    if job["conversation_id"]:
        messages = request.app.state.chat_repo.messages(job["conversation_id"])
        job["citations"] = next(
            (
                message["citations"]
                for message in messages
                if message.get("run_id") == job["run_id"]
            ),
            [],
        )
    return job


@router.post("/{key}/cancel")
async def cancel(key: str, request: Request):
    try:
        return await request.app.state.jobs.cancel(key)
    except KeyError as exc:
        raise HTTPException(404, "Task not found") from exc


@router.post("/{key}/retry", status_code=202)
async def retry(key: str, request: Request):
    try:
        return request.app.state.jobs.retry(key)
    except KeyError as exc:
        raise HTTPException(404, "Task not found") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
