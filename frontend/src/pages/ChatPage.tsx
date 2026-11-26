import SidebarContent from "../components/SidebarContent";
import { useCallback, useEffect, useRef, useState } from "react";
import { deleteChat, getChat, getModels, listChats, renameChat } from "../api/client";
import { streamChat } from "../api/sse";
import type { Conversation, ModelList, SavedMessage } from "../api/types";
import MessageBubble from "../components/MessageBubble";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<SavedMessage[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<string | null>(sessionStorage.getItem("local-agent-active"));
  const [models, setModels] = useState<ModelList | null>(null);
  const [model, setModel] = useState("");
  const [mode,setMode] = useState<"chat"|"knowledge"|"agent">("chat");
  const [reasoning,setReasoning] = useState(false);
  const [usage,setUsage] = useState<{used:number;budget:number;remaining:number;included_turns:number;total_turns:number;trimmed:boolean}|null>(null);
  useEffect(()=>{
    let cancelled=false;
    setUsage(null);
    if(active)void fetch(`/api/chats/${active}/context?reasoning=${reasoning}`).then(r=>{if(!r.ok)throw new Error();return r.json();}).then(v=>{if(!cancelled)setUsage(v);}).catch(()=>{});
    return()=>{cancelled=true;};
  },[active,reasoning,messages]);

  const [temperature,setTemperature] = useState(0.3);
  const [steps,setSteps] = useState<{seq:number;kind:string;data:Record<string,unknown>}[]>([]);
  const [menu, setMenu] = useState<{id:string; x:number; y:number} | null>(null);
  useEffect(()=>{
    if(!menu)return;
    const close=()=>setMenu(null);
    const key=(e:globalThis.KeyboardEvent)=>{if(e.key==='Escape')close();};
    window.addEventListener('click',close);window.addEventListener('keydown',key);window.addEventListener('resize',close);window.addEventListener('scroll',close,true);
    return()=>{window.removeEventListener('click',close);window.removeEventListener('keydown',key);window.removeEventListener('resize',close);window.removeEventListener('scroll',close,true);};
  },[menu]);
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
    const key=sessionStorage.getItem("local-agent-active");
    if(key) void getChat(key).then(result=>setMessages(result.messages)).catch(()=>setActive(null));
    return () => controller.current?.abort();
  }, [refresh, refreshModels]);
  useEffect(()=>{ if(active)sessionStorage.setItem("local-agent-active",active);else sessionStorage.removeItem("local-agent-active"); },[active]);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [messages]);

  const open = async (id: string) => {
    if (pending.current) return;
    pending.current = true;
    setBusy(true); setError("");
    try {
      const result = await getChat(id);
      setActive(id); setMessages(result.messages);setSteps([]);
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
      await streamChat({ message: text, model, conversation_id: key, use_knowledge_base: mode==="knowledge", mode, temperature, reasoning: reasoning && mode!=="agent" }, event => {
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
    <SidebarContent><aside className="history">
      <span className="list-label">最近</span>
      {conversations.map(chat => <div className={`history-item ${active === chat.conversation_id ? "selected" : ""}`} key={chat.conversation_id}>
        <button disabled={busy} onClick={() => void open(chat.conversation_id)}>{chat.title}</button>
        <button className="conversation-more" aria-label="会话操作" aria-haspopup="menu" aria-expanded={menu?.id===chat.conversation_id} disabled={busy} onClick={e=>{e.stopPropagation();const r=e.currentTarget.getBoundingClientRect();setMenu(menu?.id===chat.conversation_id?null:{id:chat.conversation_id,x:Math.min(r.right,window.innerWidth-176),y:Math.min(r.bottom+4,window.innerHeight-104)});}}><svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><circle cx="4" cy="9" r="1.3" fill="currentColor"/><circle cx="9" cy="9" r="1.3" fill="currentColor"/><circle cx="14" cy="9" r="1.3" fill="currentColor"/></svg></button>
      </div>)}
    </aside></SidebarContent>
    {menu&&<div className="conversation-menu" role="menu" style={{left:menu.x,top:menu.y}} onClick={e=>e.stopPropagation()}>
      <button role="menuitem" onClick={()=>{const id=menu.id;setMenu(null);const title=window.prompt('会话新名称',conversations.find(c=>c.conversation_id===id)?.title);if(title?.trim())void renameChat(id,title.trim()).then(refresh).catch(e=>setError(e.message));}}>✎ <span>重命名</span></button>
      <button role="menuitem" className="danger" onClick={()=>{const id=menu.id;setMenu(null);void remove(id);}}>⌫ <span>删除</span></button>
    </div>}
    <section className="chat">
      <header className="work-header">
        <button aria-label="新开对话" disabled={busy} onClick={()=>{setActive(null);setMessages([]);setError("");}}>✎</button>
        <div><strong>{conversations.find(c=>c.conversation_id===active)?.title || "新对话"}</strong><small>AI 生成可能有误，请核实</small></div>
        <details className="work-settings"><summary aria-label="对话设置">···</summary><div className="settings-popover">      <div className="chat-toolbar">
        <label>本地模型 <select aria-label="本地模型" value={model} disabled={busy} onChange={e => setModel(e.target.value)}>
          {!model && <option value="">暂无可用模型</option>}
          {models?.available.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
        </select></label>
        <button disabled={busy} onClick={() => void refreshModels().catch(e => setError(e.message))}>刷新</button>
        <select aria-label="工作模式" value={mode} disabled={busy} onChange={e=>setMode(e.target.value as typeof mode)}><option value="chat">自由对话</option><option value="knowledge">知识库问答</option><option value="agent">Agent 工具</option></select>
        <span className="badge">仅本地 · 只读工具</span>
      </div>
      <div className="session-toolbar">
        <label>创造性 <input aria-label="创造性" type="range" min="0" max="1" step="0.1" value={temperature} disabled={busy||mode==="agent"} onChange={e=>setTemperature(Number(e.target.value))} /> {temperature}</label>
        {active&&<button disabled={busy} onClick={()=>{const title=prompt("会话新名称",conversations.find(c=>c.conversation_id===active)?.title);if(title)void renameChat(active,title).then(refresh).catch(e=>setError(e.message));}}>重命名</button>}
        {messages.length>0&&<button disabled={busy} onClick={()=>{const content=messages.map(m=>`## ${m.role==="user"?"用户":"助手"}\n\n${m.content}`).join("\n\n");const url=URL.createObjectURL(new Blob([content],{type:"text/markdown;charset=utf-8"}));const a=document.createElement("a");a.href=url;a.download="local-agent-chat.md";a.click();URL.revokeObjectURL(url);}}>导出 Markdown</button>}
      </div>
</div></details>
      </header>
      {models?.status === "unavailable" && <p role="alert" className="error">{models.error}</p>}
      {error && <p role="alert" className="error">{error}</p>}
      <div className="messages" aria-live="polite">
        {!messages.length && <div className="empty"><h2>local-agent</h2><p>对话保存在本机。先启动 Ollama 并选择已下载的聊天模型。</p><p>开启知识库问答后，会基于已导入资料生成引用回答。</p></div>}
        {messages.map(message => <div key={message.id} id={`message-${message.id}`} className={`message-anchor ${message.role}`}><MessageBubble message={message} /></div>)}
        <div ref={end} />
      </div>
      {steps.length>0 && <details open className="run-panel"><summary>执行过程 · {steps.length} 个事件</summary>{steps.map(step=><div key={step.seq}><strong>{step.kind}</strong><pre>{JSON.stringify(step.data,null,2)}</pre></div>)}</details>}
      <div className="composer">
        <div className="composer-box">
          <textarea aria-label="消息" value={input} disabled={busy} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); } }}
            placeholder="发消息… / 切换工作模式" rows={2} />
          <div className="composer-bar">
            <span className="chip solid">本地电脑</span>
            <button type="button" className="chip" aria-pressed={reasoning} disabled={busy||mode==="agent"} onClick={()=>setReasoning(v=>!v)}>{reasoning?"深度思考":"快速回答"}</button>
            <select aria-label="输入区工作模式" value={mode} onChange={e=>setMode(e.target.value as typeof mode)}><option value="chat">自由对话</option><option value="knowledge">知识库问答</option><option value="agent">Agent 工具</option></select>
            <span className="chip">按需确认 · 只读工具</span>
            <span className="composer-spacer" />
            <span className="composer-model">{model || "暂无模型"}</span>
            {busy ? <button className="send" onClick={() => controller.current?.abort()}>停止</button>
              : <button className="send" disabled={!input.trim() || !model} onClick={() => void send()}>发送</button>}
          </div>
        </div>
      </div>
    </section>
    <aside className="console-summary chat-summary"><header className="summary-heading">对话摘要</header>
      <div className="summary-block"><h3>问题目录</h3>{messages.filter(m=>m.role==="user").map((m,i)=><button className="question-link" key={m.id} title={m.content} onClick={()=>document.getElementById(`message-${m.id}`)?.scrollIntoView({behavior:"smooth",block:"start"})}>{i+1}. {m.content}</button>)}</div>
      <div className="summary-block"><h3>上下文用量</h3>{usage?<><div className="summary-bar"><span style={{width:`${Math.min(100,100*usage.used/usage.budget)}%`}}/></div><p className="summary-line">{(usage.used/1024).toFixed(1)}K / {(usage.budget/1024).toFixed(1)}K · 剩余 {(usage.remaining/1024).toFixed(1)}K</p><p className="summary-sub">按 UTF-8 字节保守估算，非精确 token 数。历史 {usage.included_turns}/{usage.total_turns} 轮。</p>{usage.trimmed&&<p className="summary-sub">旧轮次已从模型输入裁剪，完整历史仍可查看。需要旧信息时请重新引用。</p>}</>:<p className="summary-sub">{active?"用量暂不可用":"新对话尚无历史"}</p>}</div>
      <div className="summary-block">
        <h3>当前对话</h3>
        <p className="summary-title">{conversations.find(c=>c.conversation_id===active)?.title || "新对话"}</p>
        <p className="summary-sub">{messages.length} 条消息 · {mode==="chat"?"自由对话":mode==="knowledge"?"知识库问答":"Agent 工具"}</p>
        <p className="summary-sub">模型 {model || "—"}</p>
      </div>
      <div className="summary-block">
        <h3>最近执行</h3>
        {steps.length===0
          ? <p className="summary-sub">本对话还没有工具执行记录。</p>
          : <ul className="summary-steps">{steps.slice(-6).map(step=><li key={step.seq}><code>{step.kind}</code></li>)}</ul>}
      </div>
      <div className="summary-block">
        <h3>对话产物</h3>
        {messages.length>0
          ? <button className="summary-action" disabled={busy} onClick={()=>{const content=messages.map(m=>`## ${m.role==="user"?"用户":"助手"}\n\n${m.content}`).join("\n\n");const url=URL.createObjectURL(new Blob([content],{type:"text/markdown;charset=utf-8"}));const a=document.createElement("a");a.href=url;a.download="local-agent-chat.md";a.click();URL.revokeObjectURL(url);}}>导出 Markdown</button>
          : <p className="summary-sub">还没有内容可以导出。</p>}
      </div>
      <div className="summary-block">
        <h3>策略</h3>
        <p className="summary-sub">仅连本机模型与本地索引，不外发数据。Agent 模式下的文件改动需你确认。</p>
      </div>
    </aside>
  </div>;
}
