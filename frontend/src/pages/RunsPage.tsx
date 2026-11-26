import { useEffect,useState } from "react";
import RunDetails from "../components/RunDetails";

export default function RunsPage(){
  const [runs,setRuns]=useState<{run_id:string;status:string;title:string;created_at:string;model:string}[]>([]);
  const [error,setError]=useState("");
  useEffect(()=>{void fetch("/api/runs").then(r=>{if(!r.ok)throw new Error("无法加载执行记录");return r.json();}).then(data=>setRuns(data.runs)).catch(e=>setError(e.message));},[]);
  const status:Record<string,string>={complete:"已完成",error:"失败",interrupted:"已停止",running:"运行中"};
  return <section className="runs-page"><h2>工具执行记录</h2><p>真实模型步骤和工具动作，保存在本机；不包含隐藏推理。</p>{error&&<p className="error">{error}</p>}
    {!runs.length&&<p>在Agent模式完成任务后，可在这里查看记录。</p>}
    {runs.map(run=><article className="run-item" key={run.run_id}><h3>{run.title}</h3><span>{status[run.status]||run.status} · {run.model}</span><RunDetails id={run.run_id}/></article>)}
  </section>;
}
