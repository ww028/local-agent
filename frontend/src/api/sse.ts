import type { StreamEvent } from "./types";

/**
 * Post a chat request and consume the SSE stream.
 * Callbacks are invoked as events arrive.
 */
export async function streamChat(
  body: { message: string; use_knowledge_base: boolean; conversation_id?: string | null },
  handlers: {
    onToken: (text: string) => void;
    onCitations: (citations: NonNullable<StreamEvent["citations"]>) => void;
    onDone: () => void;
    onError: (message: string) => void;
  },
): Promise<void> {
  const res = await fetch("/api/chats/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok || !res.body) {
    handlers.onError(`Request failed: ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const line = frame.trim();
      if (!line.startsWith("data:")) continue;
      const event: StreamEvent = JSON.parse(line.slice(5).trim());
      switch (event.type) {
        case "token":
          if (event.content) handlers.onToken(event.content);
          break;
        case "citation":
          if (event.citations) handlers.onCitations(event.citations);
          break;
        case "error":
          handlers.onError(event.error ?? "Unknown error");
          break;
        case "done":
          handlers.onDone();
          break;
      }
    }
  }
}
