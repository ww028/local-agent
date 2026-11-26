import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { cancelJob, getJob, getModels, listJobs, retryJob, submitJob } from "../api/client";
import type { Job } from "../api/types";
import JobDetails, { jobLabels as labels } from "../components/JobDetails";
export default function JobsPage(){
  const [jobs,setJobs]=useState<Job[]>([]);
  const [selected,setSelected]=useState<Job|null>(null);
  const [instruction,setInstruction]=useState("");
  const [models,setModels]=useState<string[]>([]);
  const [model,setModel]=useState("");
  const [diagnostics,setDiagnostics]=useState(false);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [offset,setOffset]=useState(0);
  const [params,setParams]=useSearchParams();
  const active=params.get("id");
  const alive=useRef(true);
  const inFlight=useRef(false);
  const latestSelection=useRef({active,offset});
  latestSelection.current={active,offset};

  const refresh=useCallback(async()=>{
    if(inFlight.current)return;
    inFlight.current=true;
    try{
      const [list,detail]=await Promise.all([listJobs(offset),active?getJob(active):Promise.resolve(null)]);
      if(alive.current&&latestSelection.current.active===active&&latestSelection.current.offset===offset){setJobs(list.jobs);setSelected(detail);setError("");}
    }catch(e){if(alive.current&&latestSelection.current.active===active&&latestSelection.current.offset===offset)setError(e instanceof Error?e.message:"无法读取任务状态");}
    finally{inFlight.current=false;}
  },[active,offset]);
  useEffect(()=>{
    alive.current=true;
    void refresh();
    const timer=setInterval(()=>void refresh(),2000);
    return()=>{alive.current=false;clearInterval(timer);}; // Never cancel jobs on page unload.
  },[refresh]);
  useEffect(()=>{void getModels().then(result=>{if(!alive.current)return;setModels(result.available.map(m=>m.name));setModel(result.available.some(m=>m.name===result.llm)?result.llm:result.available[0]?.name||"");}).catch(e=>setError(e.message));},[]);

  const submit=async()=>{
    if(!instruction.trim()||!model||busy)return;
    setBusy(true);setError("");
    try{
      const job=await submitJob(instruction.trim(),model,diagnostics);
      setParams({id:job.job_id});setSelected(job);setInstruction("");setOffset(0);
    }catch(e){setError(e instanceof Error?e.message:"提交失败");}
    finally{setBusy(false);}
  };
  const action=async(kind:"cancel"|"retry")=>{
    if(!selected||busy)return;
    setBusy(true);
    try{
      const job=await (kind==="cancel"?cancelJob(selected.job_id):retryJob(selected.job_id));
      setParams({id:job.job_id});setSelected(job);
      if(kind==="retry")setOffset(0);
    }catch(e){setError(e instanceof Error?e.message:"操作失败");}
    finally{setBusy(false);}
  };
  return <section className="jobs-page">
    <header><h2>后台任务中心</h2><p>下达指令后后台独立执行。刷新、换页或关闭网页不取消；电脑与后台服务需保持运行。</p></header>
    <div className="job-submit">
      <textarea aria-label="任务指令" placeholder="例如：查询8091端口被哪个进程监听（需勾选本机诊断）" value={instruction} maxLength={2000} onChange={e=>setInstruction(e.target.value)} rows={3}/>
      <div className="job-controls"><select aria-label="任务模型" value={model} onChange={e=>setModel(e.target.value)}>{!model&&<option value="">暂无本地模型</option>}{models.map(name=><option key={name}>{name}</option>)}</select>
        <label><input aria-label="允许只读本机诊断" type="checkbox" checked={diagnostics} onChange={e=>setDiagnostics(e.target.checked)}/> 允许此任务读取本机端口/系统信息</label>
        <button disabled={busy||!model||!instruction.trim()} onClick={()=>void submit()}>{busy?"提交中…":"提交后台任务"}</button></div>
      <small>只读能力：知识搜索、导入文档、计算；诊断需明确开启。不能删除文件、结束进程或操作桌面。</small>
    </div>
    {error&&<p className="error" role="alert">{error}</p>}
    <div className="job-layout"><aside className="job-list">
      {!jobs.length&&<p className="empty">暂无任务，先提交一条指令。</p>}
      {jobs.map(job=><button className={`job-item ${active===job.job_id?"selected":""}`} key={job.job_id} onClick={()=>{setParams({id:job.job_id});setSelected(job);}}><strong>{job.instruction}</strong><span className={`job-status ${job.status}`}>{labels[job.status]}</span><small>{job.summary}</small></button>)}
      <div className="job-controls"><button disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-50))}>上一页</button><button disabled={jobs.length<50} onClick={()=>setOffset(offset+50)}>下一页</button></div>
    </aside><main className="job-result">
      {selected?<JobDetails job={selected} busy={busy} onAction={kind=>void action(kind)}/>:<div className="empty"><h3>状态与结果</h3><p>选择任务查看。执行细节默认折叠。</p></div>}
    </main></div>
  </section>;
}
