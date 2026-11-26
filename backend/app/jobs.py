"""Service-owned worker: request disconnects never own or cancel its execution."""

import asyncio
import re
from contextlib import aclosing

from app.agent.executor import Executor
from app.agent.toolbox import Tools
from app.chat_context import compose_chat
from app.ollama_client import ModelError


class JobService:
    def __init__(self, state, repository):
        self.state = state
        self.repo = repository
        self.wake = asyncio.Event()
        self.worker = None
        self.active_task = None
        self.active_key = None
        self.stopping = False

    async def start(self):
        self.worker = asyncio.create_task(self._loop(), name="local-agent-job-worker")

    async def stop(self):
        self.stopping = True
        self.worker.cancel()
        if self.active_task:
            self.active_task.cancel()
        try:
            await self.worker
        except asyncio.CancelledError:
            pass

    def submit(self, instruction, model, allow_diagnostics=False, parent=None):
        # Fail early on the same bounded context used by chat.
        compose_chat(instruction, [], self.state.settings)
        job = self.repo.create(instruction, model, allow_diagnostics, parent)
        self.wake.set()
        return job

    async def cancel(self, key):
        job = self.repo.request_cancel(key)
        if self.active_key == key and self.active_task:
            self.active_task.cancel()
        self.wake.set()
        return job

    def retry(self, key):
        job = self.repo.get(key)
        if job is None:
            raise KeyError(key)
        if job["status"] not in {"failed", "cancelled", "interrupted"}:
            raise ValueError("Only failed, cancelled or interrupted jobs may be retried")
        return self.submit(job["instruction"], job["model"], job["allow_diagnostics"], key)

    async def _loop(self):
        while True:
            job = self.repo.next()
            if job is None:
                self.wake.clear()
                try:
                    await asyncio.wait_for(self.wake.wait(), timeout=1)
                except asyncio.TimeoutError:
                    pass
                continue
            # A queued job waiting behind live chat is cancellable without a
            # claimed state. After acquiring the lock always re-check SQLite.
            async with self.state.chat_lock:
                if not self.repo.claim(job["job_id"]):
                    continue
                self.active_key = job["job_id"]
                self.active_task = asyncio.create_task(self._perform(job))
                try:
                    await self.active_task
                except asyncio.CancelledError:
                    # Cancellation can arrive before the child first runs; its
                    # finally block would not execute in that case.
                    self.repo.finish(
                        job["job_id"],
                        "interrupted" if self.stopping else "cancelled",
                        error="后台服务停止" if self.stopping else None,
                    )
                    if self.stopping:
                        raise
                finally:
                    self.active_task = None
                    self.active_key = None

    async def _perform(self, job):
        key = job["job_id"]
        run_id = None
        message_id = None
        status = "interrupted"
        result = ""
        error = None
        try:
            async with asyncio.timeout(180):
                await self.state.chat_model.validate_model(job["model"])
                instruction = job["instruction"]
                required = set()
                # Exact port requests must be grounded in a successful local
                # query. An unapproved query must not invent a machine answer.
                if re.search(r"端口|\bport\b", instruction, re.I) and re.search(r"\d", instruction):
                    if not job["allow_diagnostics"]:
                        raise ModelError("本机端口查询未授权，请开启只读本机诊断后创建新任务")
                    required.add("check_port")
                conversation = self.state.chat_repo.create_conversation(
                    "任务 · " + instruction[:50]
                )
                message_id = self.state.chat_repo.start_turn(
                    conversation, instruction, job["model"]
                )
                run_id = self.state.runs.create(conversation, message_id, job["model"])
                self.repo.attach(key, conversation, run_id)
                executor = Executor(
                    self.state.chat_model,
                    Tools(self.state.knowledge, allow_diagnostics=job["allow_diagnostics"]),
                    self.state.runs,
                )
                messages = compose_chat(instruction, [], self.state.settings)
                async with aclosing(
                    executor.run(run_id, messages, job["model"], required_tools=required)
                ) as stream:
                    async for item in stream:
                        if item["type"] == "token":
                            result += item["content"]
                        elif item["type"] == "step":
                            event = item["event"]
                            summary = {
                                "model_step": "模型正在处理任务",
                                "tool_start": "执行只读工具：",
                                "tool_result": "工具返回，整理结果：",
                            }.get(event["kind"], "执行中")
                            self.repo.progress(key, summary + str(event["data"].get("tool", "")))
                status = "completed"
        except asyncio.CancelledError:
            status = "interrupted" if self.stopping else "cancelled"
            error = "后台服务停止，未自动重放任务" if self.stopping else None
            raise
        except TimeoutError:
            status = "failed"
            error = "任务超过180秒执行预算，请缩小任务范围后重试"
        except (ModelError, ValueError) as exc:
            status = "failed"
            error = str(exc)
        except Exception:
            status = "failed"
            error = "后台任务执行失败，请检查本地服务后重试"
        finally:
            self.repo.finish(key, status, result, error)
            mapped = {
                "completed": "complete",
                "failed": "error",
                "cancelled": "interrupted",
                "interrupted": "interrupted",
            }[status]
            if run_id:
                self.state.runs.finish(run_id, mapped)
            if message_id:
                self.state.chat_repo.finish(message_id, result, mapped, error)
