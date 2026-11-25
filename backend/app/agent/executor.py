"""Agent execution loop.

Registers available tools and runs the think -> act -> observe cycle. The loop
is intentionally skeletal; tool-calling parsing and multi-step iteration are
implemented incrementally.
"""

from __future__ import annotations

from app.agent.memory import Memory
from app.agent.tools.base import Tool


class Executor:
    def __init__(self, memory: Memory) -> None:
        self._memory = memory
        self._tools: dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    async def run(self, goal: str) -> str:
        # TODO: model-driven tool selection, observation feedback, loop until done.
        _ = goal
        return "Agent execution loop not implemented yet."
