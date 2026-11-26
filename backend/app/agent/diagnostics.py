"""Opt-in, read-only system diagnostics. No shell, sudo, full argv or identities."""

import asyncio
import os
import platform
import shutil
from pathlib import Path


class DiagnosticError(ValueError):
    """Safe, actionable error without raw machine output."""


async def run_fixed(args: list[str], *, timeout: float = 5) -> tuple[int, str]:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env={"PATH": "/usr/bin:/usr/sbin:/bin:/sbin", "LC_ALL": "C"},
    )

    async def collect():
        parts = []
        total = 0
        while True:
            chunk = await process.stdout.read(4096)
            if not chunk:
                break
            total += len(chunk)
            if total > 65536:
                raise DiagnosticError("Diagnostic output exceeds limit")
            parts.append(chunk)
        code = await process.wait()
        return code, b"".join(parts).decode("utf-8", errors="replace")

    try:
        return await asyncio.wait_for(collect(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise DiagnosticError("Diagnostic timed out; no port conclusion available") from exc
    finally:
        if process.returncode is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(process.wait(), timeout=1)
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                await process.wait()


def parse_lsof(text: str) -> list[dict]:
    processes = []
    current = None
    for line in text.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            current = {"pid": int(line[1:]), "process": "", "listeners": []}
            processes.append(current)
        elif current is not None and line.startswith("c"):
            current["process"] = line[1:][:120]
        elif current is not None and line.startswith("n"):
            current["listeners"].append(line[1:][:200])
    return processes


async def check_port(port: int) -> dict:
    if type(port) is not int or not 1 <= port <= 65535:
        raise DiagnosticError("Port must be an integer from 1 to 65535")
    if platform.system() not in {"Darwin", "Linux"}:
        raise DiagnosticError("Port diagnostics currently support macOS/Linux only")
    executable = next(
        (
            p
            for p in ("/usr/sbin/lsof", "/usr/bin/lsof")
            if Path(p).is_file() and os.access(p, os.X_OK)
        ),
        None,
    )
    if executable is None:
        raise DiagnosticError("lsof is not installed; cannot determine port state")
    code, text = await run_fixed(
        [
            executable,
            "-nP",
            f"-iTCP:{port}",
            "-sTCP:LISTEN",
            "-Fpcn",
        ]
    )
    if code == 1 and not text.strip():
        return {
            "port": port,
            "protocol": "TCP",
            "listening": False,
            "processes": [],
            "scope": "No visible TCP listener for the current OS user; not a UDP check",
        }
    processes = parse_lsof(text)
    # Fail closed on warnings or permissions; never report a failed lookup as free.
    if code != 0 or not processes or any(line.startswith("lsof:") for line in text.splitlines()):
        raise DiagnosticError("Port lookup failed or permissions limited; no reliable conclusion")
    return {
        "port": port,
        "protocol": "TCP",
        "listening": True,
        "processes": processes,
        "scope": "Visible listening processes only; no elevated privileges used",
    }


async def system_info() -> dict:
    memory = None
    try:
        memory = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        pass
    disk = shutil.disk_usage(Path.home().anchor or "/")
    return {
        "os": platform.system(),
        "os_version": platform.mac_ver()[0]
        if platform.system() == "Darwin"
        else platform.release(),
        "architecture": platform.machine(),
        "cpu_cores": os.cpu_count(),
        "physical_memory_bytes": memory,
        "disk_total_bytes": disk.total,
        "disk_free_bytes": disk.free,
        "note": "No hostname, username, serial number or command-line arguments collected",
    }
