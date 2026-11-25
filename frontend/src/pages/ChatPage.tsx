import { useState } from "react";
import MessageBubble from "../components/MessageBubble";
import { streamChat } from "../api/sse";
import { useChatStore } from "../store/useChatStore";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const { messages, loading, pushMessage, appendAssistantToken, setAssistantCitations, setLoading } =
    useChatStore();

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    pushMessage({ id: crypto.randomUUID(), role: "user", content: text });
    pushMessage({ id: crypto.randomUUID(), role: "assistant", content: "" });
    setLoading(true);

    await streamChat(
      { message: text, use_knowledge_base: true },
      {
        onToken: appendAssistantToken,
        onCitations: setAssistantCitations,
        onDone: () => setLoading(false),
        onError: (message) => {
          appendAssistantToken(`\n[错误] ${message}`);
          setLoading(false);
        },
      },
    );
  };

  return (
    <div className="chat">
      <div className="messages">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
      </div>
      <div className="composer">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          placeholder="输入消息…（Enter 发送，Shift+Enter 换行）"
          rows={3}
        />
        <button onClick={() => void send()} disabled={loading}>
          {loading ? "生成中…" : "发送"}
        </button>
      </div>
    </div>
  );
}
