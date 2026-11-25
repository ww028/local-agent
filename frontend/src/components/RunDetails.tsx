import { useState } from "react";

export default function RunDetails({id}:{id:string}) {
  const [events,setEvents]=useState<{seq:number;kind:string;data:Record<string,unknown>}[]|null>(null);
  const [error,setError]=useState("");
  const load=async()=>{
    try {
      const response=await fetch(`/api/runs/${encodeURIComponent(id)}`);
      if(!response.ok)throw new Error("执行记录不可用");
      setEvents((await response.json()).events);
    }catch(e){setError(e instanceof Error?e.message:"加载失败");}
  };
  return <details className="run-panel" onToggle={e=>{if(e.currentTarget.open&&!events)void load();}}><summary>查看工具执行记录</summary>
    {error&&<p className="error">{error}</p>}
    {events?.map(event=><div key={event.seq}><strong>{event.kind}</strong><pre>{JSON.stringify(event.data,null,2)}</pre></div>)}
  </details>;
}
