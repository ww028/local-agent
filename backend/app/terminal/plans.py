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


def _version_key(path):
    return tuple(int(part) for part in re.findall(r"\d+", Path(path).name))


def _nvm_bin():
    """Resolve the nvm default Node version so `node` means what the user's shell means."""
    root = Path.home() / ".nvm" / "versions" / "node"
    if not root.is_dir():
        return None
    alias = Path.home() / ".nvm" / "alias" / "default"
    chosen = None
    if alias.is_file():
        value = alias.read_text(encoding="utf-8", errors="ignore").strip()
        if value and not value.startswith("lts"):
            chosen = root / (value if value.startswith("v") else "v" + value)
    if chosen is not None and (chosen / "bin").is_dir():
        return chosen / "bin"
    versions = sorted((p for p in root.iterdir() if (p / "bin").is_dir()), key=_version_key)
    return versions[-1] / "bin" if versions else None


def _user_tool_dirs():
    """User-installed toolchains, so version queries see the same tools the user uses."""
    home = Path.home()
    candidates = [
        home / ".volta" / "bin",
        home / ".local" / "bin",
        home / ".cargo" / "bin",
        home / ".pyenv" / "shims",
        home / ".bun" / "bin",
    ]
    nvm = _nvm_bin()
    if nvm is not None:
        candidates.insert(0, nvm)
    return [str(p) for p in candidates if p.is_dir()]


USER_TOOL_DIRS = _user_tool_dirs()
SEARCH_PATH = os.pathsep.join(
    dict.fromkeys(
        [
            str(Path(sys.executable).parent),
            *USER_TOOL_DIRS,
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


SYSTEM_DIRS = {Path("/usr/bin"), Path("/bin"), Path("/usr/sbin"), Path("/sbin")}
# Accepted short-flag letters for provable read-only listing tools (combined flags allowed).
READ_ONLY_FLAGS = {"ls": set("lahtrS1dFG"), "df": set("hkmgHPi"), "du": set("hskmaxL")}
SYSCTL_READ = {
    "hw.memsize",
    "hw.physmem",
    "hw.ncpu",
    "hw.machine",
    "hw.model",
    "machdep.cpu.brand_string",
    "machdep.cpu.core_count",
    "kern.osproductversion",
    "kern.osversion",
    "kern.ostype",
    "hw.pagesize",
    "hw.cachelinesize",
}
GIT_READ = {"status", "log", "diff", "show", "rev-parse", "describe", "branch", "ls-files"}
MUTATING = [
    (r"\brm\b", "可能删除文件"),
    (r"\bmv\b", "可能移动或覆盖文件"),
    (r"\bcp\b", "可能复制或覆盖文件"),
    (r"(?:^|[ \t;|&])(?:>>?)(?![&>])", "可能写入或覆盖文件"),
    (r"\bmkdir\b|\btouch\b|\btee\b", "可能创建或写入文件"),
    (r"\b(?:brew\s+install|apt\s+install|pip3?\s+install|npm\s+(?:i|install))\b", "可能安装软件"),
    (r"\bchmod\b|\bchown\b", "可能修改文件权限"),
    (r"\bkill\b|\bpkill\b|\bkillall\b", "可能结束进程"),
    (r"\bdefaults\s+write\b|\blaunchctl\b|\bnetworksetup\b", "可能修改系统设置"),
]


def read_only_program(executable):
    """Executable lives in a fixed system dir or a known user toolchain dir (path, not trust).

    macOS exposes /bin and /usr/sbin through firmlinks, so an allowed dir is matched either
    literally or by its resolved path; a symlink pointing elsewhere still fails.
    """
    parent = Path(executable).parent
    allowed = [*sorted(SYSTEM_DIRS), *(Path(d) for d in USER_TOOL_DIRS)]
    if parent in allowed:
        return True
    resolved = parent.resolve()
    return any(resolved == Path(d).resolve() for d in allowed)


def read_only_invocation(name, args):
    """Only provable read-only invocations; used to skip confirmation, never as a sandbox."""
    if name == "uname":
        return bool(args) and set(args) <= {"-a", "-m", "-n", "-r", "-s", "-p", "-i", "-v"}
    if name == "sw_vers":
        return not args or set(args) <= {"-productName", "-productVersion", "-buildVersion"}
    if name == "sysctl":
        return len(args) == 2 and args[0] == "-n" and args[1] in SYSCTL_READ
    if name == "vm_stat":
        return not args or (len(args) == 1 and args[0].isdigit())
    if name in {"pwd", "uptime", "whoami", "date"}:
        return not args or args in (["-P"], ["-L"])
    if name == "id":
        return not args or args == ["-u"]
    if name == "ps":
        return bool(args) and set(args) <= {"-ax", "-ef", "-A", "-e"}
    if name == "lsof":
        return detect_port_query("lsof", args) is not None
    if name in READ_ONLY_FLAGS:
        letters = READ_ONLY_FLAGS[name]
        for a in args:
            if a.startswith("-"):
                if not (len(a) > 1 and set(a[1:]) <= letters):
                    return False
            elif not a:
                return False
        return True
    if name == "git":
        if args in (["--version"], ["version"]):
            return True
        return (
            bool(args)
            and args[0] in GIT_READ
            and not any(a.startswith("--output") or a == "-o" or ">" in a or "|" in a for a in args)
        )
    if name.startswith(("python", "node", "npm", "pip")):
        return args in (["--version"], ["-V"], ["-v"])
    return False


# Read-only filters: they only transform/print data. Validators below block the few flags that write.
READ_TOOLS = {
    "grep",
    "egrep",
    "fgrep",
    "cat",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "cut",
    "tr",
    "find",
    "which",
    "echo",
    "printf",
    "basename",
    "dirname",
    "file",
    "stat",
    "strings",
    "jq",
    "ps",
    "ls",
    "launchctl",
}
ALLOWED_REDIRECTS = re.compile(r"(?:[012]?>(?:>|&)?\s*/dev/null|[012]?>&\s*1)")
FORBIDDEN_SEGMENTS = {
    "sudo",
    "doas",
    "eval",
    "exec",
    "source",
    ".",
    "xargs",
    "tee",
    "sh",
    "bash",
    "zsh",
    "rm",
    "mv",
    "cp",
    "dd",
    "mkdir",
    "touch",
    "ln",
    "chmod",
    "chown",
    "kill",
    "pkill",
    "brew",
    "pip",
    "npm",
    "open",
    "curl",
    "wget",
    "nc",
    "ssh",
    "scp",
    "rsync",
}


def _read_tool_args(name, args):
    if name in {"grep", "egrep", "fgrep", "cat", "head", "tail", "wc", "cut", "tr", "echo"}:
        return True
    if name == "printf":
        return True
    if name in {"basename", "dirname", "file", "stat", "strings", "jq", "ps", "which"}:
        return True
    if name == "sort":
        return not any(a.startswith("-o") or a.startswith("--output") for a in args)
    if name == "uniq":
        return len([a for a in args if not a.startswith("-")]) <= 1
    if name == "find":
        banned = (
            "-delete",
            "-exec",
            "-execdir",
            "-ok",
            "-okdir",
            "-fprint",
            "-fprint0",
            "-fls",
            "-fprintf",
        )
        return not any(a == b or a.startswith(b + "=") for a in args for b in banned)
    if name == "launchctl":
        return args[:1] == ["list"]
    return False


def _strip_quoted(text):
    out, quote = [], None
    for ch in text:
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
            continue
        out.append(ch)
    return "".join(out)


def _shell_segments(script):
    """Split a shell script on ; | && || newline while respecting quotes."""
    parts, buf, quote = [], [], None
    for ch in script:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
        elif ch in "|;&\n":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _segment_read_only(segment):
    name = segment.split()[0]
    if name in FORBIDDEN_SEGMENTS and name != "launchctl":
        return False
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return False
    if not tokens:
        return True
    program, args = tokens[0], tokens[1:]
    resolved = shutil.which(program, path=SEARCH_PATH)
    if not resolved or not read_only_program(resolved):
        return False
    base = Path(resolved).name
    if read_only_invocation(base, args):
        return True
    return base in READ_TOOLS and _read_tool_args(base, args)


def read_only_script(script):
    """A shell script may skip confirmation only if every segment is provably read-only.

    Conservative on purpose: no output redirection (except /dev/null and 2>&1), no command
    substitution, no subshells, no background jobs, no installers or network tools.
    """
    clean = ALLOWED_REDIRECTS.sub("", script)
    bare = _strip_quoted(clean)
    if "`" in bare or "$(" in bare or "(" in bare or ")" in bare or "&" in bare.replace("&&", ""):
        return False
    if "<" in bare or ">" in bare:
        return False
    segments = _shell_segments(clean)
    if not segments:
        return False
    return all(_segment_read_only(segment) for segment in segments)


def read_only_step(step):
    if step.get("kind") == "shell":
        return read_only_script(step.get("script") or "")
    if step.get("kind") != "exec":
        return False
    return read_only_program(step.get("executable", "")) and read_only_invocation(
        Path(step["executable"]).name, step.get("args") or []
    )


def all_read_only(plan):
    steps = plan.get("steps") or []
    return bool(steps) and all(read_only_step(step) for step in steps)


OBSERVE_INTENT = re.compile(
    r"查看|看下|看看|看一下|查一下|查询|列出|列一下|是什么|是多少|多少|多大|几点|"
    r"有没有|有吗|是否|哪些|啥|什么|版本|型号|信息|占用|几个|谁在|状态|在跑|装着|装了",
    re.I,
)
# Anything that can write, delete, install or reach the network must still be confirmed,
# whatever the phrasing of the request.
WRITE_ACTIONS = [
    r"\brm\b",
    r"\brmdir\b",
    r"\bmv\b",
    r"\bcp\b",
    r"\bdd\b",
    r"\btruncate\b",
    r"\btouch\b",
    r"\bmkdir\b",
    r"\bln\b",
    r"\btee\b",
    r"\bchmod\b",
    r"\bchown\b",
    r"\bkill(?:all)?\b",
    r"\bpkill\b",
    r"\bshutdown\b|\breboot\b|\bdiskutil\b",
    r"\bsed\s+-i\b",
    r"\b(?:brew|apt|apt-get|yum|dnf|port|pip|pip3|npm|yarn|pnpm|gem|cargo|rustup|"
    r"go)\s+(?:install|uninstall|remove|rm|add|update|upgrade|get|link)\b",
    r"\bgit\s+(?:add|commit|push|pull|reset|checkout|switch|restore|clean|merge|rebase|"
    r"stash|tag|init|clone|rm|mv|apply|cherry-pick|remote|config)\b",
    r"\bgit\s+branch\s+.*-[dD]\b",
    r"(?i)\b(?:mysql|psql|sqlite3|mongosh|redis-cli)\b.*\b(?:drop|delete|truncate|insert|"
    r"update|alter|create|grant|flush|shutdown|set)\b",
    r"\bsudo\b|\bdoas\b|\bxargs\b",
    r"\b(?:sh|bash|zsh|fish|python[\d.]*|node|perl|ruby|php)\s+[^-\s]\S*",
    r"\b(?:sh|bash|zsh|fish|python[\d.]*|node|perl|ruby|php)\s+(?:-c|-e|--eval)\b",
    r"\bosascript\b|\bdefaults\s+write\b|\bnetworksetup\b|\bsystemctl\b",
    r"\blaunchctl\s+(?:load|unload|bootout|bootstrap|kickstart|enable|disable|start|stop|submit)\b",
    r"\bopen\b|\bcurl\b|\bwget\b|\bnc\b|\bssh\b|\bscp\b|\brsync\b",
    r"\bdocker\s+(?:run|rm|stop|start|restart|exec|build|push)\b",
    r"find\b.*-(?:exec|execdir|delete|ok|okdir|fprint)",
    r"\btar\b.*(?:-x|-c)\b",
]


def writes_anything(step):
    """True when a step could change files, settings, packages or reach the network."""
    raw = step.get("script") or step.get("command") or ""
    text = ALLOWED_REDIRECTS.sub("", raw)
    if re.search(r"(?<![0-9&])>>?(?![&>])", text):
        return True
    return any(re.search(pattern, text) for pattern in WRITE_ACTIONS)


def observation_proposal(instruction, steps):
    """A pure "look at something" request runs straight away unless a step can write.

    Read-only is decided by effects on the machine, not by how the request is phrased:
    a question plus a plan without any write/delete/install/network action executes
    directly; the hard blocks above still force a confirmation.
    """
    if not OBSERVE_INTENT.search(instruction or ""):
        return False
    return bool(steps) and not any(writes_anything(step) for step in steps)


def step_effects(step, read_intent=False):
    """Plain-language consequences for people who do not read command syntax."""
    if read_intent and not writes_anything(step):
        return ["只读取信息，不会修改文件或系统设置"]
    if read_only_step(step):
        return ["只读取信息，不会修改文件或系统设置"]
    found = []
    text = step.get("script") or step.get("command", "")
    for pattern, label in MUTATING:
        if re.search(pattern, text):
            found.append(label)
    if step.get("may_access_network"):
        found.append("可能访问网络")
    if step.get("kind") == "shell":
        found.insert(0, "执行脚本，可能改动文件")
    if step.get("kind") == "exec":
        found.insert(0, "运行本机程序，可能读写文件")
    if not found:
        found = ["运行程序，可能读写文件"]
    return list(dict.fromkeys(found))


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


def build_generated(workspace, relative, proposal, instruction=""):
    proposal = GeneratedProposal.model_validate(proposal)
    if proposal.unsupported_reason or not proposal.steps:
        raise ValueError(
            "未生成可执行计划：请补充明确任务；提权/密码交互不支持。模型说明不是权限判定。"
        )
    cwd = resolve_directory(workspace, relative)
    steps = []
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
            query = Path(path).parent in SYSTEM_DIRS and read_only_invocation(name, args)
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
    observation = observation_proposal(instruction, steps)
    auto_run = all_read_only({"steps": steps}) or observation
    effects = []
    for step in steps:
        effects.extend(step_effects(step, read_intent=observation))
    effects = list(dict.fromkeys(effects))
    impact = "；".join(effects) + "。取消不回滚已发生的改动。"
    warnings = (
        []
        if auto_run
        else ["这条命令以当前账号运行，能访问你的文件和网络；确认不是沙箱，只代表同意这次执行。"]
    )
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
        "instruction": instruction,
        "workspace": str(Path(workspace)),
        "relative_dir": relative,
        "cwd": str(cwd),
        "directory_device": stat.st_dev,
        "directory_inode": stat.st_ino,
        "environment": environment,
        "impact": impact,
        "effects": effects,
        "observation": observation,
        "auto_run": auto_run,
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
    rebuilt = build_generated(
        workspace, plan["relative_dir"], proposal, instruction=plan.get("instruction", "")
    )
    for item, saved in zip(rebuilt["steps"], plan["steps"]):
        item["program"] = saved["program"]
    for field in ('target_ports', 'target_identities'):
        if field in plan:
            rebuilt[field] = plan[field]  # immutable metadata already covered by digest
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
            "mysql",
            "psql",
            "sqlite3",
            "redis-server",
            "mongod",
            "docker",
            "brew",
        )
    }
    return {
        "os": platform.system(),
        "architecture": platform.machine(),
        "python": sys.executable,
        "tools": {name: path for name, path in tools.items() if path},
        # Where installed software actually lands, so "is X installed" searches the real dirs.
        "path_dirs": SEARCH_PATH.split(os.pathsep),
    }


CPU_MODEL_INTENT = re.compile("处理器|cpu|cpu型号|芯片|芯片型号", re.I)
GREP_BRE_ALT = re.compile(r"\bgrep\s+-([A-Za-z]*)\s+(['\"])((?:[^'\"]*\|)+[^'\"]*)\2")


def fix_grep_alternation(script):
    r"""Turn `grep -i 'a\|b'` (GNU BRE) into `grep -Ei 'a|b'`, which BSD grep understands."""

    def repl(match):
        flags = match.group(1)
        if "E" in flags:
            return match.group(0)
        quote = match.group(2)
        pattern = match.group(3).replace("\\|", "|")
        return "grep -E" + flags + " " + quote + pattern + quote

    return GREP_BRE_ALT.sub(repl, script)


INVENTORY_INTENT = re.compile(r"安装|装了|有啥|有哪些|都有什么|目前有|是否装|有没有装", re.I)


def fix_inventory_scope(script):
    """An `ls <dirs> | grep ...` inventory must cover the real install dirs, not a guess."""
    parts = script.split("|")
    try:
        tokens = shlex.split(parts[0].strip())
    except ValueError:
        return script
    if not tokens or Path(tokens[0]).name not in {"ls", "find"} or tokens[0] == "find":
        return script
    given = [tok for tok in tokens[1:] if not tok.startswith("-") and Path(tok).is_dir()]
    if not given:
        return script
    venv_bin = str(Path(sys.executable).parent)
    extra = [
        d
        for d in SEARCH_PATH.split(os.pathsep)
        if Path(d).is_dir() and d not in given and d != venv_bin
    ]
    if not extra:
        return script
    parts[0] = tokens[0] + " " + " ".join(given + extra)
    return " | ".join(part.strip() for part in parts)


def normalize_for_intent(instruction, proposal):
    """Deterministic fix-ups where a small local model keeps answering a nearby question."""
    steps = proposal.get("steps") or []
    if CPU_MODEL_INTENT.search(instruction):
        # "CPU 型号" needs the brand string; uname -m only reports architecture.
        only_arch = (
            len(steps) == 1
            and steps[0].get("kind", "exec") == "exec"
            and str(steps[0].get("program", "")).endswith("uname")
        )
        if only_arch and steps[0].get("args") in (["-m"], ["--machine"], []):
            args = dict(proposal)
            args["steps"] = [
                {
                    "program": "/usr/sbin/sysctl",
                    "args": ["-n", "machdep.cpu.brand_string"],
                    "description": "读取 CPU 型号",
                }
            ]
            return args
    if steps and all(step.get("kind") == "shell" for step in steps):
        fixed = dict(proposal)
        fixed["steps"] = [
            {
                **step,
                "script": (
                    fix_inventory_scope(fix_grep_alternation(step.get("script") or ""))
                    if INVENTORY_INTENT.search(instruction)
                    else fix_grep_alternation(step.get("script") or "")
                ),
            }
            for step in steps
        ]
        if any(a["script"] != b.get("script") for a, b in zip(fixed["steps"], steps)):
            return fixed
    return proposal


VERSION_TOOLS = {
    "node": "Node.js",
    "npm": "npm",
    "pnpm": "pnpm",
    "yarn": "Yarn",
    "python3": "Python",
    "pip3": "pip",
    "git": "Git",
    "go": "Go",
    "rustc": "Rust",
    "cargo": "Cargo",
    "deno": "Deno",
    "bun": "Bun",
    "java": "Java",
}
VERSION_ALIASES = {"python": "python3", "pip": "pip3", "nodejs": "node", "golang": "go"}
VERSION_STOP = re.compile(
    r"内存|cpu|核数|端口|目录|磁盘|进程|安装|升级|删除|运行|测试|状态|配置|文件", re.I
)


def detect_version_query(instruction):
    """Deterministic path for "X 版本号": no model guessing, no `which` detour.

    Returns (tool, resolved_executable_or_None); None means the request is not a pure
    version query for exactly one known tool.
    """
    if not re.search(r"版本|version", instruction, re.I) or VERSION_STOP.search(instruction):
        return None
    mentioned = []
    for name in VERSION_TOOLS:
        pattern = rf"(?<![A-Za-z0-9_.-]){re.escape(name)}(?:\.js)?(?![A-Za-z0-9_.-])"
        if re.search(pattern, instruction, re.I):
            mentioned.append(name)
    if not mentioned:
        # Any single tool name that actually resolves on this machine counts ("python 版本呢？").
        resolved_candidates = {}
        search = os.pathsep.join(
            [*USER_TOOL_DIRS, "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
        )
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_.+-]*", instruction):
            for candidate in (word, VERSION_ALIASES.get(word)):
                path = shutil.which(candidate, path=search) if candidate else None
                if path:
                    resolved_candidates[word] = (candidate, path)
                    break
        if len(resolved_candidates) != 1:
            return None
        name, path = next(iter(resolved_candidates.values()))
        return name, path
    if len(mentioned) != 1:
        return None
    if mentioned[0] in VERSION_ALIASES:
        mentioned[0] = VERSION_ALIASES[mentioned[0]]
    tool = mentioned[0]
    # Ask the machine's own toolchain first; the workbench venv only answers if nothing else exists.
    user_first = os.pathsep.join(
        dict.fromkeys(
            [
                *USER_TOOL_DIRS,
                "/opt/homebrew/bin",
                "/usr/local/bin",
                "/usr/bin",
                "/bin",
                str(Path(sys.executable).parent),
            ]
        )
    )
    return tool, shutil.which(tool, path=user_first)


def version_proposal(tool, executable):
    return {
        "goal": f"读取{tool}版本号",
        "steps": [
            {
                "program": executable,
                "args": ["--version"],
                "description": f"{VERSION_TOOLS[tool]} 版本",
            }
        ],
    }
