"""Conservative prompt budgeting. Actual tokenizer integration is deferred.

Each UTF-8 byte is conservatively budgeted as one token, plus message overhead.
This intentionally underuses the window rather than silently truncating input.
"""

from app.config import Settings
from app.rag.composer import SYSTEM_PROMPT
from app.schemas import ChatMessage


def cost(text: str) -> int:
    return len(text.encode("utf-8")) + 32


def compose_chat(text: str, history: list[ChatMessage], settings: Settings) -> list[ChatMessage]:
    available = settings.num_ctx - settings.num_predict - 512
    system = ChatMessage(role="system", content=SYSTEM_PROMPT)
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
