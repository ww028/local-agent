import SidebarContent from "../components/SidebarContent";
import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { cancelTerminal, confirmTerminal, deleteTerminalConversation, getModels, listTerminalConversations, newTerminalConversation, proposeTerminal, renameTerminalConversation, terminalCapabilities, terminalConversation, terminalTranscript } from "../api/client";
import type { TerminalTask, TerminalApproval, TerminalConversation, TerminalConversationSummary } from "../api/types";
import TerminalEntry from "../components/TerminalEntry";

const ACTIVE=['planning','queued','running','cancelling'];
const YES=['y','yes','是','执行','确认','run'];
const NO=['n','no','否','取消','不'];
const ALL_ACKS:TerminalApproval={risk_acknowledged:true,high_risk_acknowledged:true,network_acknowledged:true};

export default function TerminalPage(){
  const [tasks,setTasks]=useState<TerminalTask[]>([]);
  const [instruction,setInstruction]=useState('');const [directory,setDirectory]=useState('.');
  const [models,setModels]=useState<string[]>([]);const [model,setModel]=useState('');
  const [caps,setCaps]=useState<Awaited<ReturnType<typeof terminalCapabilities>>|null>(null);
  const [busy,setBusy]=useState(false);const [notice,setNotice]=useState('');
  const [history,setHistory]=useState<string[]>([]);const [historyIndex,setHistoryIndex]=useState(-1);
  const [conversationId,setConversationId]=useState('');const [conv,setConv]=useState<TerminalConversation|null>(null);
  const [chats,setChats]=useState<TerminalConversationSummary[]>([]);
  const [menu,setMenu]=useState<{id:string;x:number;y:number}|null>(null);
  const bodyRef=useRef<HTMLDivElement>(null);const inputRef=useRef<HTMLInputElement>(null);
  const stickyRef=useRef(true);
  const scroll=useCallback((force=false)=>{const el=bodyRef.current;if(el&&(force||stickyRef.current))el.scrollTop=el.scrollHeight;},[]);
  const load=useCallback(async()=>{
    try{const data=await terminalTranscript(30,conversationId||undefined);setTasks(data.tasks);
      const info=await terminalConversation(conversationId||undefined);
      setConv(info);if(!conversationId)setConversationId(info.conversation_id);
      const list=await listTerminalConversations();setChats(list.conversations);setNotice('');
      requestAnimationFrame(()=>scroll());}
    catch(e){setNotice(e instanceof Error?e.message:'终端记录读取失败');}
  },[conversationId]);
  const anyActive=tasks.some(t=>ACTIVE.includes(t.status));
  useEffect(()=>{void load();},[load]);
  // Follow the newest content whenever it arrives, unless the user scrolled up.
  // Timers + ResizeObserver are used because requestAnimationFrame pauses in background tabs.
  useEffect(()=>{
    const el=bodyRef.current;if(!el)return;
    const stick=()=>scroll();
    stick();
    const timers=[window.setTimeout(stick,60),window.setTimeout(stick,300)];
    const observer=new ResizeObserver(stick);
    observer.observe(el);
    return()=>{timers.forEach(id=>window.clearTimeout(id));observer.disconnect();};
  },[tasks,scroll]);
  useEffect(()=>{
    if(!anyActive)return;
    const timer=setInterval(()=>void load(),1500);
    return()=>clearInterval(timer);
  },[anyActive,load]);
  useEffect(()=>{void Promise.all([getModels(),terminalCapabilities()]).then(([m,c])=>{setModels(m.available.map(x=>x.name));setModel(m.available.some(x=>x.name===m.llm)?m.llm:m.available[0]?.name||'');setCaps(c);}).catch(e=>setNotice(e.message));},[]);

  const startNew=async()=>{
    setBusy(true);
    try{const info=await newTerminalConversation();setConversationId(info.conversation_id);setConv(info);setTasks([]);
      setChats((await listTerminalConversations()).conversations);setNotice('');scroll(true);}
    catch(e){setNotice(e instanceof Error?e.message:'新开对话失败');}
    finally{setBusy(false);inputRef.current?.focus();}
  };
  useEffect(()=>{
    if(!menu)return;
    const close=()=>setMenu(null);
    const key=(e:globalThis.KeyboardEvent)=>{if(e.key==='Escape')close();};
    window.addEventListener('click',close);window.addEventListener('keydown',key);window.addEventListener('resize',close);window.addEventListener('scroll',close,true);
    return()=>{window.removeEventListener('click',close);window.removeEventListener('keydown',key);window.removeEventListener('resize',close);window.removeEventListener('scroll',close,true);};
  },[menu]);
  const switchTo=async(id:string)=>{
    if(id===conversationId||busy)return;
    setConversationId(id);setTasks([]);setNotice('');stickyRef.current=true;
  };
  const refreshChats=async()=>{
    setChats((await listTerminalConversations()).conversations);
  };
  const renameChat=async(id:string)=>{
    const title=window.prompt('会话新名称',chats.find(c=>c.conversation_id===id)?.title);
    const trimmed=title?.trim();
    if(!trimmed)return;
    try{await renameTerminalConversation(id,trimmed);await refreshChats();}
    catch(e){setNotice(e instanceof Error?e.message:'重命名失败');}
  };
  const removeChat=async(id:string)=>{
    if(busy)return;
    try{
      await deleteTerminalConversation(id);
      if(id===conversationId)await startNew();else await refreshChats();
    }
    catch(e){setNotice(e instanceof Error?e.message:'删除失败');}
  };
  const merge=(next:TerminalTask)=>setTasks(prev=>prev.some(t=>t.task_id===next.task_id)?prev.map(t=>t.task_id===next.task_id?next:t):[...prev,next]);
  const approve=async(task:TerminalTask)=>{
    setBusy(true);
    try{merge(await confirmTerminal(task.task_id,next_hash(task),ALL_ACKS));setNotice('');}
    catch(e){setNotice(e instanceof Error?e.message:'确认失败');}
    finally{setBusy(false);void load();inputRef.current?.focus();}
  };
  const stop=async(task:TerminalTask)=>{
    setBusy(true);
    try{merge(await cancelTerminal(task.task_id));setNotice('');}
    catch(e){setNotice(e instanceof Error?e.message:'取消失败');}
    finally{setBusy(false);void load();}
  };
  const replan=async(task:TerminalTask)=>{
    setBusy(true);
    try{merge(await proposeTerminal(task.instruction,task.model||model,task.relative_dir||'.',conversationId||undefined));scroll(true);setNotice('');}
    catch(e){setNotice(e instanceof Error?e.message:'重新规划失败');}
    finally{setBusy(false);void load();}
  };
  const waiting=[...tasks].reverse().find(t=>t.status==='awaiting_confirmation');
  const submit=async()=>{
    const text=instruction.trim();if(!text||busy)return;
    if(waiting){
      const answer=text.toLowerCase();
      if(YES.includes(answer)){setInstruction('');await approve(waiting);return;}
      if(NO.includes(answer)){setInstruction('');await stop(waiting);return;}
      setNotice('当前有待确认的计划：输入 y 执行、n 取消。想换需求请先取消这份计划。');return;
    }
    if(!model){setNotice('本机暂无可用模型');return;}
    setBusy(true);
    try{merge(await proposeTerminal(text,model,directory,conversationId||undefined));setHistory(h=>[...h,text].slice(-50));setHistoryIndex(-1);setInstruction('');setNotice('');scroll(true);}
    catch(e){setNotice(e instanceof Error?e.message:'规划失败');}
    finally{setBusy(false);inputRef.current?.focus();}
  };
  const onKeyDown=(event:KeyboardEvent<HTMLInputElement>)=>{
    if(event.key==='ArrowUp'&&history.length){event.preventDefault();const next=historyIndex<0?history.length-1:Math.max(0,historyIndex-1);setHistoryIndex(next);setInstruction(history[next]||'');}
    if(event.key==='ArrowDown'&&historyIndex>=0){event.preventDefault();const next=historyIndex+1;if(next>=history.length){setHistoryIndex(-1);setInstruction('');}else{setHistoryIndex(next);setInstruction(history[next]||'');}}
  };
  const convTitle=chats.find(c=>c.conversation_id===conversationId)?.title||'新对话';
  return <section className="console-page">
    <SidebarContent><aside className="console-chats">
      <div className="console-chats-head">
        <span className="list-label">最近</span>
      </div>
      <div className="console-chats-list">
        {chats.map(item=><div key={item.conversation_id} className={`console-chat${item.conversation_id===conversationId?' active':''}`}>
          <button type="button" className="console-chat-open" onClick={()=>void switchTo(item.conversation_id)} title={`${item.task_count} 条记录`}>
            <span className="console-chat-title">{item.title}</span>
            <span className="console-chat-meta">{item.task_count} 条 · {shortTime(item.updated_at)}</span>
          </button>
          <button className="conversation-more" aria-label="会话操作" aria-haspopup="menu" aria-expanded={menu?.id===item.conversation_id} disabled={busy} onClick={e=>{e.stopPropagation();const r=e.currentTarget.getBoundingClientRect();setMenu(menu?.id===item.conversation_id?null:{id:item.conversation_id,x:Math.min(r.right,window.innerWidth-176),y:Math.min(r.bottom+4,window.innerHeight-104)});}}><svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><circle cx="4" cy="9" r="1.3" fill="currentColor"/><circle cx="9" cy="9" r="1.3" fill="currentColor"/><circle cx="14" cy="9" r="1.3" fill="currentColor"/></svg></button>
        </div>)}
        {!chats.length&&<p className="t-dim">还没有对话，直接在右侧提问开始。</p>}
      </div>
    </aside></SidebarContent>
    {menu&&<div className="conversation-menu" role="menu" style={{left:menu.x,top:menu.y}} onClick={e=>e.stopPropagation()}>
      <button role="menuitem" onClick={()=>{const id=menu.id;setMenu(null);void renameChat(id);}}>✎ <span>重命名</span></button>
      <button role="menuitem" className="danger" onClick={()=>{const id=menu.id;setMenu(null);void removeChat(id);}}>⌫ <span>删除</span></button>
    </div>}
    <div className="terminal-window">
      <div className="terminal-titlebar">
        <button aria-label="新开终端对话" onClick={()=>void startNew()} disabled={busy}>✎</button><div className="work-title"><strong>{convTitle}</strong><small>本地 AI 终端 · 改动按需确认</small></div>
        <details className="work-settings"><summary aria-label="终端设置">···</summary><span className="terminal-tools settings-popover">
          <select aria-label="终端模型" value={model} onChange={e=>setModel(e.target.value)}>{!model&&<option value="">无模型</option>}{models.map(m=><option key={m}>{m}</option>)}</select>
          <input aria-label="终端相对目录" maxLength={240} value={directory} onChange={e=>setDirectory(e.target.value)} placeholder="相对目录"/>
        </span></details>
      </div>
      <div className="terminal-body" ref={bodyRef} onScroll={()=>{const el=bodyRef.current;if(el)stickyRef.current=el.scrollHeight-el.scrollTop-el.clientHeight<140;}}>
        {!tasks.length&&<div className="t-empty">
    
          <p>这是一个本地 AI 终端。用自然语言描述需求，AI 生成真实命令；只读查询直接执行，会改动文件或系统设置的才让你确认。</p>
          <p className="t-dim">例如：查看电脑内存 · 统计仓库文件数量 · 运行项目测试 · 检查 8092 端口</p>
        </div>}
        {tasks.map(task=><div key={task.task_id} id={`terminal-${task.task_id}`}><TerminalEntry task={task} busy={busy} onConfirm={()=>void approve(task)} onCancel={()=>void stop(task)} onReplan={()=>void replan(task)}/></div>)}
        {notice&&<p className="t-fail" role="alert">{notice}</p>}
      </div>
      {waiting&&<div className="t-pending-bar">有待确认的计划：在下方输入 <kbd>y</kbd> 执行、<kbd>n</kbd> 取消，或点上方按钮</div>}
      <form className={`terminal-prompt ${waiting?'awaiting':''}`} onSubmit={event=>{event.preventDefault();void submit();}}>
        <span className="ps1"><b>❯</b></span>
        <input ref={inputRef} aria-label="终端对话输入" autoComplete="off" spellCheck={false}
          placeholder={waiting?'待确认：输入 y 执行 / n 取消':busy?'处理中…':'用自然语言描述你想在终端做的事，回车发送'}
          value={instruction} disabled={busy} onChange={e=>setInstruction(e.target.value)} onKeyDown={onKeyDown}/>
      </form>
      <footer className="terminal-foot">
        <span>{caps?.workspace||'读取工作区…'}</span>
        {conv?<span className="t-usage" title={`模型窗口 ${conv.budget_bytes} 字节：固定提示 ${conv.system_bytes} + 实际送入历史 ${conv.history_bytes}${conv.raw_history_bytes>conv.history_bytes?`（原始历史 ${conv.raw_history_bytes}，已按预算截断）`:''}`}>
          上下文 {kb(conv.used_bytes)} / {kb(conv.budget_bytes)}（{conv.percent}%）· 历史 {conv.turns}/{conv.raw_turns} 轮 · 剩 {kb(conv.remaining_bytes)}
        </span>:<span>读取上下文用量…</span>}
        <span>生成式命令 · 只读自动执行 · 改动才确认 · 非交互式 PTY · 计划 10 分钟有效</span>
      </footer>
    </div>
    <aside className="console-summary"><header className="summary-heading">对话摘要</header><div className="summary-block"><h3>问题目录</h3>{tasks.map((t,i)=><button key={t.task_id} className="question-link" title={t.instruction} onClick={()=>document.getElementById(`terminal-${t.task_id}`)?.scrollIntoView({behavior:"smooth",block:"start"})}>{i+1}. {t.instruction}</button>)}</div>
      <div className="summary-block">
        <h3>上下文</h3>
        {conv?<>
          <div className="summary-bar"><span style={{width:`${conv.percent}%`}} className={conv.percent>85?'hot':''}/></div>
          <p className="summary-line">{kb(conv.used_bytes)} / {kb(conv.budget_bytes)}（{conv.percent}%）</p>
          <p className="summary-sub">固定提示 {kb(conv.system_bytes)} · 历史 {conv.turns}/{conv.raw_turns} 轮</p>
          <p className="summary-sub">剩余 {kb(conv.remaining_bytes)}{conv.raw_history_bytes>conv.history_bytes?` · 原始历史 ${kb(conv.raw_history_bytes)}，已裁剪`:''}</p>
        </>:<p className="summary-sub">读取中…</p>}
      </div>
      <div className="summary-block">
        <h3>当前对话</h3>
        <p className="summary-line">{convTitle}</p>
        <p className="summary-sub">{tasks.length} 条记录 · 模型 {model||'未选择'}</p>
        <p className="summary-sub">目录 {directory}</p>
      </div>
      <div className="summary-block">
        <h3>最近执行</h3>
        {[...tasks].reverse().slice(0,5).map(task=><div key={task.task_id} className="summary-task">
          <span className={`summary-dot ${task.status}`}/>
          <span className="summary-task-text">{task.instruction}</span>
        </div>)}
        {!tasks.length&&<p className="summary-sub">本对话还没有执行记录。</p>}
      </div>
      <div className="summary-block">
        <h3>策略</h3>
        <p className="summary-sub">只读查询直接执行；改动文件、装软件、联网需确认。计划 10 分钟内有效，最多 4 步。</p>
      </div>
    </aside>
  </section>;
}

function shortTime(iso:string){
  const d=new Date(iso);const now=new Date();
  if(d.toDateString()===now.toDateString())return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
  return `${d.getMonth()+1}/${d.getDate()}`;
}
function kb(bytes:number){return `${(bytes/1024).toFixed(1)}K`;}
function next_hash(task:TerminalTask){return task.plan_hash||'';}
