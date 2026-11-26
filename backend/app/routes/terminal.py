"""Generated command planning and hash-bound explicit user approvals."""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.terminal.plans import POLICY

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
    risk_acknowledged: bool = Field(default=False, strict=True)
    high_risk_acknowledged: bool = Field(default=False, strict=True)
    network_acknowledged: bool = Field(default=False, strict=True)


@router.get("/capabilities")
async def capabilities(request: Request):
    return {
        "workspace": str(request.app.state.settings.terminal_workspace),
        "policy_version": POLICY,
        "actions": [],
        "scope": "AI生成实际exec命令或完整shell脚本，只读查询直接执行；可能修改文件或系统设置、联网的命令需确认后执行；不是OS沙箱，不支持提权密码/交互式输入。",
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


@router.get("/transcript")
async def transcript(request: Request, limit: int = Query(20, ge=1, le=50)):
    return {"tasks": request.app.state.terminal.repo.transcript(limit)}


@router.get("/{key}")
async def detail(key: str, request: Request):
    task = request.app.state.terminal.repo.get(key)
    if not task:
        raise HTTPException(404, "终端任务不存在")
    return task


@router.post("/{key}/confirm")
async def confirm(key: str, body: Confirm, request: Request):
    try:
        return request.app.state.terminal.confirm(
            key, body.plan_hash, **body.model_dump(exclude={"plan_hash"})
        )
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
