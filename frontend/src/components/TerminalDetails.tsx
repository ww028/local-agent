import { useState } from "react";
import type { TerminalTask, TerminalApproval } from "../api/types";
import MessageBubble from "./MessageBubble";

export const terminalLabels:Record<string,string>={planning:"AI规划中",awaiting_confirmation:"等待你确认",queued:"已确认·排队中",running:"执行中",cancelling:"正在停止",completed:"命令完成",failed:"失败",cancelled:"已取消",interrupted:"服务中断",expired:"确认过期"};
export default function TerminalDetails({task,busy,onConfirm,onCancel,onReplan}:{task:TerminalTask;busy:boolean;onConfirm:(approval:TerminalApproval)=>void;onCancel:()=>void;onReplan:()=>void}){
  const [approval,setApproval]=useState<TerminalApproval>({risk_acknowledged:false,high_risk_acknowledged:false,network_acknowledged:false});
  const allowed=(!task.plan?.requires_risk_ack||approval.risk_acknowledged)&&(!task.plan?.requires_high_risk_ack||approval.high_risk_acknowledged)&&(!task.plan?.requires_network_ack||approval.network_acknowledged);
  return <>
    <h3>{task.instruction}</h3><p className="job-status">{terminalLabels[task.status]||task.status}</p>
    {task.error&&<p role="alert" className="error">{task.error}</p>}
    {task.plan&&<section className="terminal-plan"><h4>AI理解与待确认命令计划</h4><p>{task.plan.goal}</p>
      <p>执行目录：{task.plan.cwd}</p><p className="badge">{task.plan.impact}</p>
      {task.plan.warnings?.map((w,i)=><p className="error" key={i}>{w}</p>)}
      {task.plan.steps.map((step,index)=><div key={index} className="terminal-command"><strong>{index+1}. {step.description}</strong><p className="badge">{step.kind==='shell'?'完整Shell脚本':'直接程序/参数'} · {step.risk==='high'?'高风险/影响待审核':'只读查询提示（非安全保证）'}</p><pre>{step.command}</pre><small>最多 {step.timeout_seconds} 秒 · {step.risk_reason||'旧版固定命令'}</small>{step.may_access_network&&<p className="error">可能联网：静态提示不能证明离线，需单独确认。</p>}</div>)}
      <details><summary>执行环境（未继承全部环境变量）</summary><pre>{JSON.stringify(task.plan.environment,null,2)}</pre></details>
      {task.status==='awaiting_confirmation'&&<><p>此计划尚未执行。确认只对应上面这份固定内容；改命令、参数、目录后须重新确认。</p><p className="badge">确认期限：{new Date(task.expires_at||'').toLocaleString()}</p>
        {task.plan.requires_risk_ack&&<p><label><input type="checkbox" aria-label="确认账号权限与无沙箱" checked={approval.risk_acknowledged} onChange={e=>setApproval({...approval,risk_acknowledged:e.target.checked})}/> 我已审核命令，理解以当前账号运行、无OS沙箱，取消不回滚。</label></p>}
        {task.plan.requires_high_risk_ack&&<p><label><input type="checkbox" aria-label="确认高风险影响" checked={approval.high_risk_acknowledged} onChange={e=>setApproval({...approval,high_risk_acknowledged:e.target.checked})}/> 我确认上述代码执行、文件修改及其他实际影响。</label></p>}
        {task.plan.requires_network_ack&&<p><label><input type="checkbox" aria-label="确认可能联网" checked={approval.network_acknowledged} onChange={e=>setApproval({...approval,network_acknowledged:e.target.checked})}/> 我允许这份计划可能的网络访问，理解没有网络隔离。</label></p>}
        <button className="confirm-command" disabled={busy||!allowed} onClick={()=>onConfirm(approval)}>确认执行以上命令</button></>}
    </section>}
    {['planning','awaiting_confirmation','queued','running','cancelling'].includes(task.status)&&<button disabled={busy||task.status==='cancelling'} onClick={onCancel}>{task.status==='running'?'停止本任务':'取消任务'}</button>}
    {['failed','cancelled','interrupted','expired'].includes(task.status)&&<button disabled={busy} onClick={onReplan}>按原需求重新规划（需再次确认）</button>}
    {!!task.steps?.length&&<section><h4>实际命令输出 · 事实记录</h4>{task.steps.map(step=><article className="terminal-output" key={step.step_index}><strong>步骤{step.step_index+1} · {terminalLabels[step.status]||step.status} · 退出码 {step.exit_code??'尚未结束'}</strong>
      {step.error&&<p className="error">{step.error}</p>}{step.facts&&<section className="port-facts"><h4>本机 {step.facts.port} 端口 · {step.facts.protocol} 监听查询</h4><p>{step.facts.listening?'发现可见监听进程':'当前用户可见范围未发现TCP监听'}</p>{step.facts.processes.map((p,i)=><p key={i}>进程：{p.process} · PID：{p.pid} · 地址：{p.listeners.join('、')}</p>)}<p className="badge">{step.facts.scope} · 查询无需联网</p></section>}<p>标准输出</p><pre>{step.stdout||'（无输出）'}</pre><p>错误输出</p><pre>{step.stderr||'（无输出）'}</pre></article>)}</section>}
    {task.summary&&<section><h4>AI结果解释（不替代原始输出）</h4><MessageBubble message={{id:0,role:'assistant',content:task.summary,status:'complete',model:task.model}}/></section>}
  </>;
}
