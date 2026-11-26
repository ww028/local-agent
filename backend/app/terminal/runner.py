"""Bounded confirmed subprocess execution, including reviewed shell scripts."""

import asyncio
import os
import re
import signal

LIMIT = 128 * 1024


def display_text(data):
    text = data.decode("utf-8", errors="replace")
    text = re.sub(r"\x1b\][^\x07]*(?:\x07|\x1b\\)", "", text)
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    return "".join(c for c in text if c in "\n\t" or ord(c) >= 32 and ord(c) != 127)


async def execute_step(step, plan, on_output):
    process = await asyncio.create_subprocess_exec(
        step["executable"],
        *step["args"],
        cwd=plan["cwd"],
        env=plan["environment"],
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    total = 0
    status = "completed"
    error = None

    async def read(name, stream):
        nonlocal total
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                return
            left = max(0, LIMIT - total)
            buffers[name].extend(chunk[:left])
            total += len(chunk)
            on_output(display_text(buffers["stdout"]), display_text(buffers["stderr"]))
            if total > LIMIT:
                raise ValueError("命令输出超过128KiB，已停止，不代表完整结果")

    readers = [
        asyncio.create_task(read("stdout", process.stdout)),
        asyncio.create_task(read("stderr", process.stderr)),
    ]
    try:
        async with asyncio.timeout(step["timeout_seconds"]):
            await asyncio.gather(*readers)
            code = await process.wait()
        if code != 0:
            name = step["executable"].rsplit("/", 1)[-1]
            detail = (display_text(buffers["stderr"]).strip().splitlines() or [""])[0][:160]
            reason = f"：{detail}" if detail else "（该命令没有任何说明输出）"
            status, error = "failed", f"{name} 退出码 {code}{reason}；后续步骤未执行"
    except asyncio.CancelledError:
        status = "cancelled"
        raise
    except TimeoutError:
        status, error = "failed", f"命令超过{step['timeout_seconds']}秒预算，已停止"
    except ValueError as exc:
        status, error = "failed", str(exc)
    finally:
        for reader in readers:
            if not reader.done():
                reader.cancel()
        await asyncio.gather(*readers, return_exceptions=True)
        # The group belongs to this launch only; cleanup includes descendants.
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                break
            if sig == signal.SIGTERM:
                try:
                    await asyncio.wait_for(process.wait(), timeout=0.3)
                except TimeoutError:
                    pass
                await asyncio.sleep(0.05)
        await process.wait()
    facts = None
    if step.get("action") == "check_port" and (error is None or "退出码" in error):
        from app.agent.diagnostics import DiagnosticError, port_result

        try:
            facts = port_result(
                step["port"],
                process.returncode,
                display_text(buffers["stdout"]),
                display_text(buffers["stderr"]),
            )
            status, error = "completed", None
        except DiagnosticError as exc:
            status, error = "failed", str(exc)
    return {
        "facts": facts,
        "status": status,
        "exit_code": process.returncode,
        "stdout": display_text(buffers["stdout"]),
        "stderr": display_text(buffers["stderr"]),
        "error": error,
    }
