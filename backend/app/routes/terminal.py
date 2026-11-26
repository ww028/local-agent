"""Confirmed read-only terminal API; no client-supplied executable or argv."""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.terminal.catalog import ACTIONS

router = APIRouter(prefix="/api/terminal", tags=["terminal"])


class Submit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instruction: str = Field(min_length=1, max_length=2000)
    relative_dir: str = Field(default=".", max_length=240)
    model: str | None = Field(default=None, max_length=200)

    @field_validator("instruction")
    @classmethod
    def trim(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("指令不能为空")
        return value


class Confirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


@router.get("/capabilities")
async def capabilities(request: Request):
    return {
        "workspace": str(request.app.state.settings.terminal_workspace),
        "actions": [{"action": k, "description": v[0]} for k, v in ACTIONS.items()],
        "scope": "仅固定只读命令；不是OS沙箱；无任意shell/写入/提权/联网/交互输入",
    }


@router.post("", status_code=202)
async def submit(body: Submit, request: Request):
    try:
        return request.app.state.terminal.submit(
            body.instruction, body.model or request.app.state.settings.llm_model, body.relative_dir
        )
    except (ValueError, OSError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("")
async def listing(
    request: Request, limit: int = Query(50, ge=1, le=50), offset: int = Query(0, ge=0)
):
    return {"tasks": request.app.state.terminal.repo.list(limit, offset)}


@router.get("/{key}")
async def detail(key: str, request: Request):
    task = request.app.state.terminal.repo.get(key)
    if not task:
        raise HTTPException(404, "终端任务不存在")
    return task


@router.post("/{key}/confirm")
async def confirm(key: str, body: Confirm, request: Request):
    try:
        return request.app.state.terminal.confirm(key, body.plan_hash)
    except KeyError as exc:
        raise HTTPException(404, "终端任务不存在") from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/{key}/cancel")
async def cancel(key: str, request: Request):
    try:
        return await request.app.state.terminal.cancel(key)
    except KeyError as exc:
        raise HTTPException(404, "终端任务不存在") from exc
