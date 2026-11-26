import { useState } from "react";

const labels:Record<string,string>={model_step:"模型决策",tool_start:"调用工具",tool_result:"工具结果"};
export default function RunDetails({id}:{id:string}) {
  const [events,setEvents]=useState<{seq:number;kind:string;data:Record<string,unknown>}[]|null>(null);
  const [error,setError]=useState("");
  const load=async()=>{try{const r=await fetch(`/api/runs/${encodeURIComponent(id)}`);if(!r.ok)throw new Error("记录不可用");setEvents((await r.json()).events);}catch(e){setError(e instanceof Error?e.message:"加载失败");}};
  return <details className="run-panel" onToggle={e=>{if(e.currentTarget.open&&!events)void load();}}><summary>查看工具执行记录</summary>
    {error&&<p className="error">{error}</p>}
    {events?.map(event=><div className="run-event" key={event.seq}><strong>{event.seq}. {labels[event.kind]||event.kind} {String(event.data.tool||"")}</strong>
      <details><summary>参数和结果</summary><pre>{JSON.stringify(event.data,null,2)}</pre></details></div>)}
  </details>;
}
