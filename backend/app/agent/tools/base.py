"""Tool interface for the agent executor.

A tool exposes a JSON-schema-ish description and an async ``run`` method. New
tools are added under this package and registered in the executor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ToolResult:
    output: str
    data: dict[str, Any] | None = None


class Tool(Protocol):
    name: str
    description: str

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        ...
