import { describe, expect, it } from "vitest";
import { consumeSSE } from "./sse";
import type { StreamEvent } from "./types";

function stream(text: string, stride = 1) {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (let i = 0; i < bytes.length; i += stride) controller.enqueue(bytes.slice(i, i + stride));
      controller.close();
    },
  });
}
describe("SSE reader", () => {
  it("handles arbitrary UTF-8 byte boundaries and CRLF", async () => {
    const seen: StreamEvent[] = [];
    await consumeSSE(stream('data: {"type":"token","content":"你好"}\r\n\r\ndata: {"type":"done"}\r\n\r\n'), event => seen.push(event));
    expect(seen.map(e => e.type)).toEqual(["token", "done"]);
    expect(seen[0].content).toBe("你好");
  });
  it("rejects a premature end", async () => {
    await expect(consumeSSE(stream('data: {"type":"token","content":"x"}\n\n'), () => undefined)).rejects.toThrow("before generation completed");
  });
  it("recognizes terminal error", async () => {
    const seen: StreamEvent[] = [];
    await consumeSSE(stream('data: {"type":"error","error":"offline"}\n\n'), e => seen.push(e));
    expect(seen[0].error).toBe("offline");
  });
  it("rejects malformed JSON", async () => {
    await expect(consumeSSE(stream("data: not-json\n\n"), () => undefined)).rejects.toThrow();
  });
  it("handles terminal frame without trailing newline", async () => {
    await consumeSSE(stream('data: {"type":"done"}'), () => undefined);
  });
});
