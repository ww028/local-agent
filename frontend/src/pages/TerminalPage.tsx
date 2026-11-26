import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { cancelTerminal, confirmTerminal, getModels, getTerminal, listTerminal, proposeTerminal, terminalCapabilities } from "../api/client";
import type { TerminalTask, TerminalApproval } from "../api/types";
import TerminalDetails, { terminalLabels } from "../components/TerminalDetails";

export default function TerminalPage(){
  const [params,setParams]=useSearchParams();const id=params.get('id');
  const [tasks,setTasks]=useState<TerminalTask[]>([]);const [task,setTask]=useState<TerminalTask|null>(null);
  const [instruction,setInstruction]=useState('');const [directory,setDirectory]=useState('.');
  const [models,setModels]=useState<string[]>([]);const [model,setModel]=useState('');
  const [caps,setCaps]=useState<Awaited<ReturnType<typeof terminalCapabilities>>|null>(null);
  const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [offset,setOffset]=useState(0);
  useEffect(()=>{
    let alive=true;let inFlight=false;
    const refresh=async()=>{
      if(inFlight)return;inFlight=true;
      try{const [list,detail]=await Promise.all([listTerminal(offset),id?getTerminal(id):Promise.resolve(null)]);
        if(alive){setTasks(list.tasks);setTask(detail);setError('');}
      }catch(e){if(alive)setError(e instanceof Error?e.message:'任务读取失败');}finally{inFlight=false;}
    };
    void refresh();const timer=setInterval(()=>void refresh(),1500);
    return()=>{alive=false;clearInterval(timer);}; // No cancellation on navigation.
  },[id,offset]);
  useEffect(()=>{
    let alive=true;
    void Promise.all([getModels(),terminalCapabilities()]).then(([m,c])=>{if(!alive)return;setModels(m.available.map(x=>x.name));setModel(m.available.some(x=>x.name===m.llm)?m.llm:m.available[0]?.name||'');setCaps(c);}).catch(e=>{if(alive)setError(e.message);});
    return()=>{alive=false;};
  },[]);
  const submit=async()=>{
    if(busy||!model||!instruction.trim())return;setBusy(true);
    try{const next=await proposeTerminal(instruction.trim(),model,directory);setTask(next);setParams({id:next.task_id});setOffset(0);setInstruction('');setError('');}
    catch(e){setError(e instanceof Error?e.message:'规划失败');}finally{setBusy(false);}
  };
  const action=async(kind:'confirm'|'cancel'|'replan',approval?:TerminalApproval)=>{
    if(!task||busy)return;setBusy(true);
    try{const next=kind==='confirm'?await confirmTerminal(task.task_id,task.plan_hash||'',approval):kind==='cancel'?await cancelTerminal(task.task_id):await proposeTerminal(task.instruction,task.model||model,task.relative_dir||'.');
      setTask(next);setParams({id:next.task_id});setError('');if(kind==='replan')setOffset(0);
    }catch(e){setError(e instanceof Error?e.message:'操作失败');}finally{setBusy(false);}
  };
  return <section className="jobs-page">
    <header><h2>AI终端</h2><p>先理解和展示命令，确认后才执行。离开网页不取消已确认任务；电脑与后台需保持运行。</p></header>
    <section className="job-submit"><textarea aria-label="终端任务指令" rows={3} maxLength={2000} value={instruction} onChange={e=>setInstruction(e.target.value)} placeholder="例如：查看电脑内存大小、运行项目测试，或用管道整理一份文件列表。"/>
      <div className="job-controls"><label>相对目录 <input aria-label="终端相对目录" maxLength={240} value={directory} onChange={e=>setDirectory(e.target.value)}/></label><select aria-label="终端模型" value={model} onChange={e=>setModel(e.target.value)}>{!model&&<option value="">暂无本地模型</option>}{models.map(m=><option key={m}>{m}</option>)}</select><button disabled={busy||!model||!instruction.trim()} onClick={()=>void submit()}>生成命令计划（不执行）</button></div>
      <small>工作区：{caps?.workspace||'读取中…'}</small><details><summary>生成式命令与权限说明</summary><p>{caps?.scope}</p><p>AI可生成系统查询、开发命令和完整脚本，不局限于预置功能。所有命令先审核确认；可能读写文件/执行代码/联网需额外确认。无OS沙箱、无网络隔离；不支持管理员密码、交互式输入或常驻服务。计划10分钟内有效。</p></details>
    </section>
    {error&&<p role="alert" className="error">{error}</p>}
    <div className="job-layout"><aside className="job-list">{!tasks.length&&<p className="empty">先描述需求，AI只规划，不会直接执行。</p>}{tasks.map(t=><button key={t.task_id} className={`job-item ${id===t.task_id?'selected':''}`} onClick={()=>{setParams({id:t.task_id});setTask(null);}}><strong>{t.instruction}</strong><small>{terminalLabels[t.status]||t.status}</small></button>)}<div className="job-controls"><button disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-50))}>上一页</button><button disabled={tasks.length<50} onClick={()=>setOffset(offset+50)}>下一页</button></div></aside>
      <main className="job-result">{task?<TerminalDetails key={task.task_id+task.plan_hash} task={task} busy={busy} onConfirm={approval=>void action('confirm',approval)} onCancel={()=>void action('cancel')} onReplan={()=>void action('replan')}/>:<div className="empty"><h3>计划 → 确认 → 结果</h3><p>选择历史任务或提交新需求。</p></div>}</main></div>
  </section>;
}
