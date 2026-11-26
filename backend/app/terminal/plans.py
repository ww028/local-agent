"""Generated command plans: approval is not a sandbox or a safety guarantee."""

import os
import platform
import re
import shlex
import shutil
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.terminal.catalog import canonical, digest, resolve_directory

POLICY = "generated-terminal-v3"
SEARCH_PATH = os.pathsep.join(
    dict.fromkeys(
        [
            str(Path(sys.executable).parent),
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin",
        ]
    )
)


class CommandStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["exec", "shell"] = "exec"
    program: str = Field(default="", max_length=500)
    args: list[str] = Field(default_factory=list, max_length=64)
    script: str = Field(default="", max_length=8000)
    description: str = Field(min_length=1, max_length=600)
    timeout_seconds: int = Field(default=30, strict=True, ge=1, le=300)

    @model_validator(mode="after")
    def shape(self):
        values = [self.program, self.script, self.description, *self.args]
        if any("\x00" in value for value in values) or sum(len(a) for a in self.args) > 12000:
            raise ValueError("命令包含无效字符或参数过长")
        if self.kind == "exec" and (not self.program or self.script):
            raise ValueError("exec需要program/args，不可同时带script")
        if self.kind == "shell" and (not self.script.strip() or self.program or self.args):
            raise ValueError("shell需要完整script，不可同时带program/args")
        return self


class GeneratedProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: str = Field(min_length=1, max_length=600)
    steps: list[CommandStep] = Field(default_factory=list, max_length=4)
    unsupported_reason: str = Field(default="", max_length=600)


def executable(program, cwd=None):
    expanded = Path(program).expanduser()
    if cwd is not None and not expanded.is_absolute() and "/" in program:
        expanded = Path(cwd) / expanded
        program = str(expanded)
    if any(c.isspace() for c in program) and not Path(program).is_absolute():
        raise ValueError("program只能是程序名，命令参数应放在args")
    candidate = (
        str(Path(program).expanduser())
        if Path(program).is_absolute()
        else shutil.which(program, path=SEARCH_PATH)
    )
    if not candidate or not Path(candidate).is_file() or not os.access(candidate, os.X_OK):
        raise ValueError("本机程序不可用：" + program + "；没有自动安装")
    return str(Path(candidate).resolve())


def readonly_query(name, args):
    # Used only to improve warnings, never as an execution allowlist.
    if name in {"pwd", "sw_vers", "uname", "uptime"}:
        return not any(a.startswith("--") for a in args)
    if name == "sysctl":
        return bool(args) and "-w" not in args and not any("=" in a for a in args)
    if name in {"ls", "df", "du", "vm_stat", "free"}:
        return all(not any(c in a for c in "\n\r") for a in args)
    if name == "lsof":
        return True
    if name == "git":
        return args == ["--version"]
    return name.startswith(("python", "node", "npm")) and args in (["--version"], ["-V"])


def detect_port_query(path, args):
    if (
        Path(path).name != "lsof"
        or len(args) != 4
        or args[0] != "-nP"
        or args[2:] != ["-sTCP:LISTEN", "-Fpcn"]
    ):
        return None
    match = re.fullmatch(r"-iTCP:(\d+)", args[1])
    if not match or not 1 <= int(match[1]) <= 65535:
        return None
    return int(match[1])


def build_generated(workspace, relative, proposal):
    proposal = GeneratedProposal.model_validate(proposal)
    if proposal.unsupported_reason or not proposal.steps:
        raise ValueError(
            "未生成可执行计划：请补充明确任务；提权/密码交互不支持。模型说明不是权限判定。"
        )
    cwd = resolve_directory(workspace, relative)
    steps = []
    warnings = ["命令以当前用户账号运行，可访问该账号的文件和网络；初始工作目录限制不是OS沙箱。"]
    high = False
    network = False
    for item in proposal.steps:
        raw = item.script if item.kind == "shell" else shlex.join([item.program, *item.args])
        if re.search(r"(?:^|[\s;|&/])(sudo|su|doas|pkexec)(?:\s|$)", raw):
            raise ValueError("此终端不提供管理员提权或密码交互，请移除提权步骤")
        if re.search(r"(?:\.ssh/|\.aws/|\.gnupg/|Keychains/)", raw, re.I):
            raise ValueError("不能通过AI终端操作凭据目录；请移除该步骤")
        if item.kind == "shell":
            path = executable("/bin/bash")
            args = ["--noprofile", "--norc", "-o", "pipefail", "-c", item.script]
            risk = "high"
            may_network = True
            reason = "完整shell脚本可执行代码、修改文件或联网；请逐行审核，静态提示不能证明安全。"
        else:
            path = executable(item.program, cwd)
            args = list(item.args)
            name = Path(path).name
            query = Path(path).parent in {
                Path("/usr/bin"),
                Path("/bin"),
                Path("/usr/sbin"),
                Path("/sbin"),
            } and readonly_query(name, args)
            risk = "low" if query else "high"
            may_network = not query or bool(re.search(r"https?://|ssh://", raw))
            reason = (
                "常见只读查询，仍需核对目标/参数。"
                if query
                else "该命令可能运行项目代码、修改文件或联网，实际影响须由你审核。"
            )
        high |= risk == "high"
        network |= may_network
        st = Path(path).stat()
        step = {
            "kind": item.kind,
            "program": item.program,
            "script": item.script,
            "executable": path,
            "args": args,
            "description": item.description,
            "timeout_seconds": item.timeout_seconds,
            "command": item.script if item.kind == "shell" else shlex.join([path, *args]),
            "risk": risk,
            "risk_reason": reason,
            "may_access_network": may_network,
            "executable_identity": {
                "device": st.st_dev,
                "inode": st.st_ino,
                "size": st.st_size,
                "mtime_ns": st.st_mtime_ns,
            },
        }
        port = detect_port_query(path, args)
        if port is not None:
            step.update({"action": "check_port", "port": port})
        steps.append(step)
    stat = cwd.stat()
    environment = {
        "PATH": SEARCH_PATH,
        "HOME": str(Path.home()),
        "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
        "LANG": "en_US.UTF-8",
        "LC_ALL": "C",
        "GIT_TERMINAL_PROMPT": "0",
        "PAGER": "cat",
        "GIT_PAGER": "cat",
        "PYTHONUNBUFFERED": "1",
    }
    return {
        "policy_version": POLICY,
        "goal": proposal.goal,
        "workspace": str(Path(workspace)),
        "relative_dir": relative,
        "cwd": str(cwd),
        "directory_device": stat.st_dev,
        "directory_inode": stat.st_ino,
        "environment": environment,
        "impact": "生成式命令计划；可能读写文件或联网，以完整命令和风险提示为准；取消不回滚。",
        "risk": "high" if high else "low",
        "warnings": warnings,
        "requires_risk_ack": True,
        "requires_high_risk_ack": high,
        "requires_network_ack": network,
        "steps": steps,
    }


def verify_generated(workspace, plan, expected_hash):
    if digest(plan) != expected_hash:
        raise ValueError("计划内容已改变，请重新生成并确认")
    proposal = {
        "goal": plan["goal"],
        "steps": [
            {
                "kind": s["kind"],
                "program": s["program"],
                "args": s["args"] if s["kind"] == "exec" else [],
                "script": s["script"],
                "description": s["description"],
                "timeout_seconds": s["timeout_seconds"],
            }
            for s in plan["steps"]
        ],
    }
    # program binds to its originally resolved executable even if PATH changes.
    for item, saved in zip(proposal["steps"], plan["steps"]):
        if item["kind"] == "exec":
            item["program"] = saved["executable"]
    rebuilt = build_generated(workspace, plan["relative_dir"], proposal)
    for item, saved in zip(rebuilt["steps"], plan["steps"]):
        item["program"] = saved["program"]
    if canonical(rebuilt) != canonical(plan):
        raise ValueError("目录、程序、环境或策略已变化，必须重新规划")
    return rebuilt


def verify_any(workspace, plan, expected_hash):
    if plan.get("policy_version") == POLICY:
        return verify_generated(workspace, plan, expected_hash)
    from app.terminal.catalog import verify_plan

    return verify_plan(workspace, plan, expected_hash)


def planning_context():
    tools = {
        name: shutil.which(name, path=SEARCH_PATH)
        for name in (
            "sysctl",
            "vm_stat",
            "free",
            "df",
            "du",
            "lsof",
            "git",
            "node",
            "npm",
            "python3",
            "uname",
            "bash",
        )
    }
    return {
        "os": platform.system(),
        "architecture": platform.machine(),
        "python": sys.executable,
        "tools": {name: path for name, path in tools.items() if path},
    }
