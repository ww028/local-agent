"""Fixed read-only action catalog. Model text is never executable input."""

import hashlib
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

POLICY = "readonly-terminal-v1"
ACTIONS = {
    "list_directory": ("列出当前目录（含隐藏项目名）", "/bin/ls", ["-la", "."]),
    "show_directory": ("显示当前工作目录", "/bin/pwd", ["-P"]),
    "git_status": (
        "检查Git修改状态，不修改索引",
        "/usr/bin/git",
        ["status", "--short", "--branch", "--untracked-files=normal", "--ignore-submodules=all"],
    ),
    "git_diff_stat": (
        "查看未暂存和已暂存差异统计",
        "/usr/bin/git",
        [
            "diff",
            "HEAD",
            "--stat",
            "--no-ext-diff",
            "--no-textconv",
            "--ignore-submodules=all",
            "--no-renames",
        ],
    ),
    "git_recent_commits": (
        "查看最近5条提交，不验签或执行外部程序",
        "/usr/bin/git",
        ["log", "-5", "--no-show-signature", "--format=%h %s", "--no-decorate"],
    ),
    "git_version": ("查看Git版本", "/usr/bin/git", ["--version"]),
    "python_version": ("查看后端Python版本", sys.executable, ["-I", "--version"]),
}
Action = Literal[
    "list_directory",
    "show_directory",
    "git_status",
    "git_diff_stat",
    "git_recent_commits",
    "git_version",
    "python_version",
]
ENV = {
    "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
    "LC_ALL": "C",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_PAGER": "cat",
    "PAGER": "cat",
}
BLOCKED = {".git", ".ssh", ".aws", ".gnupg", ".config", ".ollama", "data", "node_modules", ".venv"}


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: str = Field(min_length=1, max_length=400)
    actions: list[Action] = Field(max_length=4)
    unsupported_reason: str = Field(default="", max_length=600)


def canonical(plan):
    return json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(plan):
    return hashlib.sha256(canonical(plan).encode()).hexdigest()


def workspace_path(value):
    raw = Path(value).absolute()
    if raw != raw.resolve() or not raw.is_dir():
        raise ValueError("工作区必须是存在的非符号链接项目目录")
    if raw == Path(raw.anchor) or raw == Path.home() or raw.name in BLOCKED:
        raise ValueError("不能把根目录、家目录或敏感目录作为终端工作区")
    if any(part in {".ssh", ".aws", ".gnupg", ".config", ".ollama"} for part in raw.parts):
        raise ValueError("不能选择凭据或敏感工作区")
    return raw


def resolve_directory(workspace, relative):
    root = workspace_path(workspace)
    if not isinstance(relative, str) or len(relative) > 240:
        raise ValueError("执行目录无效")
    parts = Path(relative).parts
    if Path(relative).is_absolute() or any(
        p == ".." or p in BLOCKED or p.startswith(".env") for p in parts
    ):
        raise ValueError("只能选择项目内非敏感、无上级跳转的相对目录")
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("执行目录不能经过符号链接")
    target = current.resolve(strict=True)
    if not target.is_relative_to(root) or not target.is_dir():
        raise ValueError("执行目录不属于项目")
    return target


def check_git_directory(root, cwd):
    current = cwd
    while current.is_relative_to(root):
        dotgit = current / ".git"
        if dotgit.exists() or dotgit.is_symlink():
            if not dotgit.is_dir() or dotgit.is_symlink():
                raise ValueError("首批不支持Git工作树指针或符号链接元数据")
            for item in ("config", "commondir", "objects", "refs", "HEAD", "index"):
                path = dotgit / item
                if path.is_symlink() or (item == "commondir" and path.exists()):
                    raise ValueError("Git元数据包含外部指针，不支持此项目")
            return
        if current == root:
            break
        current = current.parent
    raise ValueError("指定项目内没有可用Git仓库")


def build_plan(workspace, relative, proposal):
    proposal = Proposal.model_validate(proposal)
    if proposal.unsupported_reason or not proposal.actions:
        raise ValueError(proposal.unsupported_reason or "模型未提出可执行步骤")
    root = workspace_path(workspace)
    cwd = resolve_directory(root, relative)
    steps = []
    for action in proposal.actions:
        description, executable, args = ACTIONS[action]
        if not Path(executable).is_file() or not os.access(executable, os.X_OK):
            raise ValueError("所需固定程序不可用：" + action)
        args = list(args)
        if action.startswith("git_") and action != "git_version":
            check_git_directory(root, cwd)
        if action.startswith("git_"):
            args = [
                "--no-pager",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.hooksPath=" + os.devnull,
                "-c",
                "core.quotePath=true",
                "-c",
                "color.ui=false",
            ] + args
        steps.append(
            {
                "action": action,
                "description": description,
                "executable": executable,
                "args": args,
                "command": shlex.join([executable, *args]),
                "timeout_seconds": 30,
            }
        )
    stat = cwd.stat()
    return {
        "policy_version": POLICY,
        "goal": proposal.goal,
        "workspace": str(root),
        "relative_dir": relative,
        "cwd": str(cwd),
        "directory_device": stat.st_dev,
        "directory_inode": stat.st_ino,
        "environment": {**ENV, "GIT_CEILING_DIRECTORIES": str(root.parent)},
        "impact": "只读；无任意shell、写入、提权、联网或交互输入。工作目录限制不是OS沙箱。",
        "steps": steps,
    }


def verify_plan(workspace, plan, expected_hash):
    if digest(plan) != expected_hash:
        raise ValueError("计划已变化，必须重新规划确认")
    rebuilt = build_plan(
        workspace,
        plan["relative_dir"],
        {"goal": plan["goal"], "actions": [s["action"] for s in plan["steps"]]},
    )
    if canonical(rebuilt) != canonical(plan):
        raise ValueError("目录、程序或策略已变化，请重新规划确认")
    return rebuilt
