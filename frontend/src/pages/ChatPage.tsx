import { useCallback, useEffect, useRef, useState } from "react";
import { deleteChat, getChat, getModels, listChats, renameChat } from "../api/client";
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
  const [mode,setMode] = useState<"chat"|"knowledge"|"agent">("chat");
  const [search,setSearch] = useState("");
  const [temperature,setTemperature] = useState(0.3);
  const [steps,setSteps] = useState<{seq:number;kind:string;data:Record<string,unknown>}[]>([]);
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
    setInput(""); setError(""); setBusy(true); setSteps([]);
    setMessages(previous => [...previous,
      { id: userId, role: "user", content: text, status: "complete" },
      { id: assistantId, role: "assistant", content: "", status: "generating", model }]);
    const update = (fn: (message: SavedMessage) => SavedMessage) =>
      setMessages(previous => previous.map(m => m.id === assistantId ? fn(m) : m));
    try {
      await streamChat({ message: text, model, conversation_id: key, use_knowledge_base: mode==="knowledge", mode, temperature }, event => {
        if (event.type === "meta" && event.conversation_id) {
          key = event.conversation_id; setActive(key);
          if(event.run_id) update(m=>({...m,run_id:event.run_id}));
        } else if(event.type === "step" && event.event) {
          const step=event.event;
          setSteps(previous=>[...previous,step]);
        } else if (event.type === "token") {
          update(m => ({ ...m, content: m.content + (event.content ?? "") }));
        } else if (event.type === "citation") {
          update(m => ({ ...m, citations: event.citations ?? [] }));
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
      <input aria-label="搜索会话" className="history-search" placeholder="搜索会话" value={search} onChange={e=>setSearch(e.target.value)} />
      {conversations.filter(chat=>chat.title.toLowerCase().includes(search.toLowerCase())).map(chat => <div className={`history-item ${active === chat.conversation_id ? "selected" : ""}`} key={chat.conversation_id}>
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
        <select aria-label="工作模式" value={mode} disabled={busy} onChange={e=>setMode(e.target.value as typeof mode)}><option value="chat">自由对话</option><option value="knowledge">知识库问答</option><option value="agent">Agent 工具</option></select>
        <span className="badge">仅本地 · 只读工具</span>
      </header>
      <div className="session-toolbar">
        <label>创造性 <input aria-label="创造性" type="range" min="0" max="1" step="0.1" value={temperature} disabled={busy||mode==="agent"} onChange={e=>setTemperature(Number(e.target.value))} /> {temperature}</label>
        {active&&<button disabled={busy} onClick={()=>{const title=prompt("会话新名称",conversations.find(c=>c.conversation_id===active)?.title);if(title)void renameChat(active,title).then(refresh).catch(e=>setError(e.message));}}>重命名</button>}
        {messages.length>0&&<button disabled={busy} onClick={()=>{const content=messages.map(m=>`## ${m.role==="user"?"用户":"助手"}\n\n${m.content}`).join("\n\n");const url=URL.createObjectURL(new Blob([content],{type:"text/markdown;charset=utf-8"}));const a=document.createElement("a");a.href=url;a.download="local-agent-chat.md";a.click();URL.revokeObjectURL(url);}}>导出 Markdown</button>}
      </div>
      {models?.status === "unavailable" && <p role="alert" className="error">{models.error}</p>}
      {error && <p role="alert" className="error">{error}</p>}
      <div className="messages" aria-live="polite">
        {!messages.length && <div className="empty"><h2>local-agent</h2><p>对话保存在本机。先启动 Ollama 并选择已下载的聊天模型。</p><p>开启知识库问答后，会基于已导入资料生成引用回答。</p></div>}
        {messages.map(message => <MessageBubble key={message.id} message={message} />)}
        <div ref={end} />
      </div>
      {steps.length>0 && <details open className="run-panel"><summary>执行过程 · {steps.length} 个事件</summary>{steps.map(step=><div key={step.seq}><strong>{step.kind}</strong><pre>{JSON.stringify(step.data,null,2)}</pre></div>)}</details>}
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
