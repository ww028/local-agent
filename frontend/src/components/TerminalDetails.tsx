import type { TerminalTask } from "../api/types";
import MessageBubble from "./MessageBubble";

export const terminalLabels:Record<string,string>={planning:"AI规划中",awaiting_confirmation:"等待你确认",queued:"已确认·排队中",running:"执行中",cancelling:"正在停止",completed:"命令完成",failed:"失败",cancelled:"已取消",interrupted:"服务中断",expired:"确认过期"};
export default function TerminalDetails({task,busy,onConfirm,onCancel,onReplan}:{task:TerminalTask;busy:boolean;onConfirm:()=>void;onCancel:()=>void;onReplan:()=>void}){
  return <>
    <h3>{task.instruction}</h3><p className="job-status">{terminalLabels[task.status]||task.status}</p>
    {task.error&&<p role="alert" className="error">{task.error}</p>}
    {task.plan&&<section className="terminal-plan"><h4>AI理解与固定执行计划</h4><p>{task.plan.goal}</p>
      <p>执行目录：{task.plan.cwd}</p><p className="badge">{task.plan.impact}</p>
      {task.plan.steps.map((step,index)=><div key={index} className="terminal-command"><strong>{index+1}. {step.description}</strong><pre>{step.command}</pre><small>最多 {step.timeout_seconds} 秒 · 固定程序与参数，无 shell</small></div>)}
      <details><summary>执行环境</summary><pre>{JSON.stringify(task.plan.environment,null,2)}</pre></details>
      {task.status==="awaiting_confirmation"&&<><p>此计划尚未执行。确认仅对上面这份固定计划有效，改动后必须重新确认。</p><p className="badge">确认期限：{new Date(task.expires_at||"").toLocaleString()}</p><button className="confirm-command" disabled={busy} onClick={onConfirm}>确认执行以上命令</button></>}
    </section>}
    {["planning","awaiting_confirmation","queued","running","cancelling"].includes(task.status)&&<button disabled={busy||task.status==="cancelling"} onClick={onCancel}>{task.status==="running"?"停止本任务":"取消任务"}</button>}
    {["failed","cancelled","interrupted","expired"].includes(task.status)&&<button disabled={busy} onClick={onReplan}>按原需求重新规划（需再次确认）</button>}
    {!!task.steps?.length&&<section><h4>实际命令输出 · 事实记录</h4>{task.steps.map(step=><article className="terminal-output" key={step.step_index}><strong>步骤{step.step_index+1} · {terminalLabels[step.status]||step.status} · 退出码 {step.exit_code??"尚未结束"}</strong>
      {step.error&&<p className="error">{step.error}</p>}{step.facts&&<section className="port-facts"><h4>本机 {step.facts.port} 端口 · {step.facts.protocol} 监听查询</h4><p>{step.facts.listening?'发现可见监听进程':'当前用户可见范围未发现TCP监听'}</p>{step.facts.processes.map((p,i)=><p key={i}>进程：{p.process} · PID：{p.pid} · 地址：{p.listeners.join('、')}</p>)}<p className="badge">{step.facts.scope} · 查询无需联网</p></section>}<p>标准输出</p><pre>{step.stdout||"（无输出）"}</pre><p>错误输出</p><pre>{step.stderr||"（无输出）"}</pre></article>)}</section>}
    {task.summary&&<section><h4>AI结果解释（不替代原始输出）</h4><MessageBubble message={{id:0,role:"assistant",content:task.summary,status:"complete",model:task.model}}/></section>}
  </>;
}
