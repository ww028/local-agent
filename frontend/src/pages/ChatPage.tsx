import { useCallback, useEffect, useRef, useState } from "react";
import { deleteChat, getChat, getModels, listChats } from "../api/client";
import { streamChat } from "../api/sse";
import type { Conversation, ModelList, SavedMessage } from "../api/types";
import MessageBubble from "../components/MessageBubble";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<SavedMessage[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [models, setModels] = useState<ModelList | null>(null);
  const [model, setModel] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const controller = useRef<AbortController | null>(null);
  const pending = useRef(false);
  const end = useRef<HTMLDivElement>(null);

  const refresh = useCallback(async () => {
    const result = await listChats();
    setConversations(result.conversations);
  }, []);
  const refreshModels = useCallback(async () => {
    const result = await getModels();
    setModels(result);
    setModel(previous => result.available.some(m => m.name === previous) ? previous
      : result.available.some(m => m.name === result.llm) ? result.llm
      : result.available[0]?.name ?? "");
  }, []);
  useEffect(() => {
    void Promise.all([refresh(), refreshModels()]).catch(e => setError(String(e.message)));
    return () => controller.current?.abort();
  }, [refresh, refreshModels]);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [messages]);

  const open = async (id: string) => {
    if (pending.current) return;
    pending.current = true;
    setBusy(true); setError("");
    try {
      const result = await getChat(id);
      setActive(id); setMessages(result.messages);
    } catch (e) { setError(e instanceof Error ? e.message : "会话加载失败"); }
    finally { pending.current = false; setBusy(false); }
  };
  const remove = async (id: string) => {
    if (busy || !window.confirm("删除这个会话和本地历史？")) return;
    try {
      await deleteChat(id);
      if (id === active) { setActive(null); setMessages([]); }
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "删除失败"); }
  };
  const send = async () => {
    const text = input.trim();
    if (!text || pending.current || !model) return;
    pending.current = true;
    const abort = new AbortController();
    controller.current = abort;
    let key = active;
    const userId = -Date.now();
    const assistantId = userId - 1;
    setInput(""); setError(""); setBusy(true);
    setMessages(previous => [...previous,
      { id: userId, role: "user", content: text, status: "complete" },
      { id: assistantId, role: "assistant", content: "", status: "generating", model }]);
    const update = (fn: (message: SavedMessage) => SavedMessage) =>
      setMessages(previous => previous.map(m => m.id === assistantId ? fn(m) : m));
    try {
      await streamChat({ message: text, model, conversation_id: key }, event => {
        if (event.type === "meta" && event.conversation_id) {
          key = event.conversation_id; setActive(key);
        } else if (event.type === "token") {
          update(m => ({ ...m, content: m.content + (event.content ?? "") }));
        } else if (event.type === "done") {
          update(m => ({ ...m, status: "complete" }));
        } else if (event.type === "error") {
          update(m => ({ ...m, status: "error", error: event.error ?? "生成失败" }));
        }
      }, abort.signal);
    } catch (e) {
      if (abort.signal.aborted) update(m => ({ ...m, status: "interrupted" }));
      else {
        const detail = e instanceof Error ? e.message : "请求失败";
        setError(detail); update(m => ({ ...m, status: "error", error: detail }));
      }
    } finally {
      // Keep local partial output when cancellation happens before the server
      // has finished recording it. Opening the conversation later reloads it.
      if (key && !abort.signal.aborted) {
        try { setMessages((await getChat(key)).messages); }
        catch { setError("无法刷新历史，本次回答仍显示在页面中。"); }
      }
      try { await refresh(); } catch { /* Existing chat remains usable. */ }
      controller.current = null; pending.current = false; setBusy(false);
    }
  };

  return <div className="workbench">
    <aside className="history">
      <button disabled={busy} onClick={() => { setActive(null); setMessages([]); setError(""); }}>＋ 新会话</button>
      {conversations.map(chat => <div className={`history-item ${active === chat.conversation_id ? "selected" : ""}`} key={chat.conversation_id}>
        <button disabled={busy} onClick={() => void open(chat.conversation_id)}>{chat.title}</button>
        <button aria-label="删除会话" disabled={busy} onClick={() => void remove(chat.conversation_id)}>×</button>
      </div>)}
    </aside>
    <section className="chat">
      <header className="chat-toolbar">
        <label>本地模型 <select aria-label="本地模型" value={model} disabled={busy} onChange={e => setModel(e.target.value)}>
          {!model && <option value="">暂无可用模型</option>}
          {models?.available.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
        </select></label>
        <button disabled={busy} onClick={() => void refreshModels().catch(e => setError(e.message))}>刷新</button>
        <span className="badge">本地 · 纯聊天</span>
      </header>
      {models?.status === "unavailable" && <p role="alert" className="error">{models.error}</p>}
      {error && <p role="alert" className="error">{error}</p>}
      <div className="messages" aria-live="polite">
        {!messages.length && <div className="empty"><h2>local-agent</h2><p>对话保存在本机。先启动 Ollama 并选择已下载的聊天模型。</p><p>知识库检索将在后续阶段开放。</p></div>}
        {messages.map(message => <MessageBubble key={message.id} message={message} />)}
        <div ref={end} />
      </div>
      <div className="composer">
        <textarea aria-label="消息" value={input} disabled={busy} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); } }}
          placeholder="Enter 发送 · Shift+Enter 换行" rows={3} />
        {busy ? <button onClick={() => controller.current?.abort()}>停止生成</button>
          : <button disabled={!input.trim() || !model} onClick={() => void send()}>发送</button>}
      </div>
    </section>
  </div>;
}
