"""Conservative prompt budgeting. Actual tokenizer integration is deferred.

Each UTF-8 byte is conservatively budgeted as one token, plus message overhead.
This intentionally underuses the window rather than silently truncating input.
"""

from app.config import Settings
from app.rag.composer import SYSTEM_PROMPT
from app.schemas import ChatMessage


def cost(text: str) -> int:
    return len(text.encode("utf-8")) + 32


def compose_chat(text: str, history: list[ChatMessage], settings: Settings, *, output_budget: int | None = None, reasoning: bool = False) -> list[ChatMessage]:
    available = settings.num_ctx - (output_budget or settings.num_predict) - 512
    system = ChatMessage(role="system", content=SYSTEM_PROMPT)
    if reasoning:
        system.content += "\n严格按当前题目的目标和明确条件作答。不要套用相似题目的默认限制；在内部检查结论是否满足全部条件，最终只给结论和必要的简短解释。"
    remaining = available - cost(system.content) - cost(text)
    if remaining < 0:
        raise ValueError("Message exceeds the configured input budget. Shorten it or raise NUM_CTX.")
    selected: list[ChatMessage] = []
    for i in range(len(history) - 2, -1, -2):
        pair = history[i:i + 2]
        required = sum(cost(m.content) for m in pair)
        if required > remaining:
            break
        selected = pair + selected
        remaining -= required
    return [system, *selected, ChatMessage(role="user", content=text)]
