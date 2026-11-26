import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { cancelTerminal, confirmTerminal, getModels, newTerminalConversation, proposeTerminal, terminalCapabilities, terminalConversation, terminalTranscript } from "../api/client";
import type { TerminalTask, TerminalApproval, TerminalConversation } from "../api/types";
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
  const bodyRef=useRef<HTMLDivElement>(null);const inputRef=useRef<HTMLInputElement>(null);
  const stickyRef=useRef(true);
  const scroll=useCallback((force=false)=>{const el=bodyRef.current;if(el&&(force||stickyRef.current))el.scrollTop=el.scrollHeight;},[]);
  const load=useCallback(async()=>{
    try{const data=await terminalTranscript(30,conversationId||undefined);setTasks(data.tasks);
      const info=await terminalConversation(conversationId||undefined);
      setConv(info);if(!conversationId)setConversationId(info.conversation_id);setNotice('');
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
    try{const info=await newTerminalConversation();setConversationId(info.conversation_id);setConv(info);setTasks([]);setNotice('');scroll(true);}
    catch(e){setNotice(e instanceof Error?e.message:'新开对话失败');}
    finally{setBusy(false);inputRef.current?.focus();}
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
    try{merge(await proposeTerminal(task.instruction,task.model||model,task.relative_dir||'.'));scroll(true);setNotice('');}
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
  return <section className="console-page">
    <div className="terminal-window">
      <div className="terminal-titlebar">
        <span className="terminal-title">local-agent — zsh — 80×24</span>
        <span className="terminal-tools">
          <button type="button" className="t-new-chat" title="清空当前上下文，开始一段新对话" onClick={()=>void startNew()} disabled={busy}>新开对话</button>
          <select aria-label="终端模型" value={model} onChange={e=>setModel(e.target.value)}>{!model&&<option value="">无模型</option>}{models.map(m=><option key={m}>{m}</option>)}</select>
          <input aria-label="终端相对目录" maxLength={240} value={directory} onChange={e=>setDirectory(e.target.value)} placeholder="相对目录"/>
        </span>
      </div>
      <div className="terminal-body" ref={bodyRef} onScroll={()=>{const el=bodyRef.current;if(el)stickyRef.current=el.scrollHeight-el.scrollTop-el.clientHeight<140;}}>
        {!tasks.length&&<div className="t-empty">
          <p className="t-dim">Last login: {new Date().toLocaleString()} on local-agent</p>
          <p>这是一个本地 AI 终端。用自然语言描述需求，AI 生成真实命令；只读查询直接执行，会改动文件或系统设置的才让你确认。</p>
          <p className="t-dim">例如：查看电脑内存 · 统计仓库文件数量 · 运行项目测试 · 检查 8092 端口</p>
        </div>}
        {tasks.map(task=><TerminalEntry key={task.task_id} task={task} busy={busy} onConfirm={()=>void approve(task)} onCancel={()=>void stop(task)} onReplan={()=>void replan(task)}/>)}
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
  </section>;
}

function kb(bytes:number){return `${(bytes/1024).toFixed(1)}K`;}
function next_hash(task:TerminalTask){return task.plan_hash||'';}
