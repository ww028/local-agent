"""Task planner.

Turns a user goal into an ordered list of steps. The first version can rely on
the model's own tool-calling decisions; a dedicated planning step can be added
later for multi-step tasks.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlanStep:
    action: str
    tool: str | None
    arguments: dict


class Planner:
    # TODO: produce structured plans, optionally via a planning prompt.
    def plan(self, goal: str) -> list[PlanStep]:
        return [PlanStep(action="answer", tool=None, arguments={"goal": goal})]
