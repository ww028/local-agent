import type { StreamEvent } from "./types";
import { responseError } from "./client";

/** Incremental UTF-8 SSE reader with cancellation, CRLF and EOF validation. */
export async function consumeSSE(
  stream: ReadableStream<Uint8Array>, onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let terminal = false;
  const parse = (frame: string) => {
    const data = frame.split(/\r?\n/).filter(line => line.startsWith("data:"))
      .map(line => line.slice(5).trimStart()).join("\n");
    if (!data) return;
    const event = JSON.parse(data) as StreamEvent;
    if (!["meta", "token", "citation", "step", "error", "done"].includes(event.type)) {
      throw new Error("Invalid stream event.");
    }
    terminal ||= event.type === "done" || event.type === "error";
    onEvent(event);
  };
  try {
    while (!terminal) {
      const { value, done } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      let boundary: RegExpExecArray | null;
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        parse(buffer.slice(0, boundary.index));
        buffer = buffer.slice(boundary.index + boundary[0].length);
        if (terminal) break;
      }
      if (done) {
        if (buffer.trim() && !terminal) parse(buffer);
        break;
      }
    }
    if (!terminal) throw new Error("Connection ended before generation completed.");
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}
export async function streamChat(
  body: { reasoning?: boolean; message: string; model: string; conversation_id?: string | null; use_knowledge_base?: boolean; temperature?: number; mode?: "chat"|"knowledge"|"agent" },
  onEvent: (event: StreamEvent) => void, signal: AbortSignal,
): Promise<void> {
  const response = await fetch("/api/chats/stream", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body), signal,
  });
  if (!response.ok) throw new Error(await responseError(response));
  if (!response.body) throw new Error("Streaming is unavailable.");
  await consumeSSE(response.body, onEvent);
}
