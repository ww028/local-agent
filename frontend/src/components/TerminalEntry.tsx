import type { TerminalTask, TerminalApproval } from "../api/types";

export const terminalLabels:Record<string,string>={planning:"AI 生成命令中",awaiting_confirmation:"等待确认",queued:"准备执行",running:"执行中",cancelling:"正在停止",completed:"已结束",failed:"失败",cancelled:"已取消",interrupted:"服务中断",expired:"确认已过期"};

const ALL_ACKS:TerminalApproval={risk_acknowledged:true,high_risk_acknowledged:true,network_acknowledged:true};

/** A single exchange in the console transcript: request → plan → confirmation → output. */
export default function TerminalEntry({task,busy,onConfirm,onCancel,onReplan}:{task:TerminalTask;busy:boolean;onConfirm:(approval:TerminalApproval)=>void;onCancel:()=>void;onReplan:()=>void}){
  const plan=task.plan;
  const pending=task.status==='awaiting_confirmation';
  return <article className="t-entry">
    <p className="t-user"><span className="t-promptbox">❯</span> {task.instruction}</p>
    {task.status==='planning'&&<p className="t-dim">AI 正在理解需求并生成命令…<span className="t-caret"/></p>}
    {plan&&<div className="t-plan">
      <p className="t-ai"><span className="t-ainame">AI</span> {plan.goal}</p>
      <p className="t-dim">执行目录 {plan.cwd}</p>
      {plan.warnings?.map((w,i)=><p className="t-warn" key={i}>⚠ {w}</p>)}
      {plan.steps.map((step,index)=><div className="t-cmd" key={index}>
        <p className="t-dim">{plan.steps.length>1?`${index+1}. `:''}{step.description} · {step.risk==='high'?'需审核影响':'常见只读查询'}{step.may_access_network?' · 可能联网':''}</p>
        <pre className="t-command">{step.command}</pre>
        {step.risk_reason&&<p className="t-note">{step.risk_reason}</p>}
        {step.may_access_network&&<p className="t-note">可能联网：静态提示不能证明离线，需在确认中一并接受。</p>}
      </div>)}
    </div>}
    {pending&&<div className="t-confirm">
      <p>执行以上命令？输入 <kbd>y</kbd> 执行，<kbd>n</kbd> 取消<span className="t-caret"/></p>
      <p className="t-note">y = 允许{plan?.requires_high_risk_ack?'执行代码/修改文件、':''}{plan?.requires_network_ack?'可能的网络访问、':''}以当前账号运行（无 OS 沙箱）。确认绑定这份命令，{new Date(task.expires_at||'').toLocaleTimeString()} 前有效。</p>
      <p className="t-actions"><button disabled={busy} onClick={()=>onConfirm(ALL_ACKS)}>执行 (y)</button><button disabled={busy} onClick={onCancel}>取消 (n)</button></p>
    </div>}
    {task.status==='queued'&&<p className="t-dim">已确认，等待执行…</p>}
    {task.status==='running'&&<p className="t-dim">执行中…<span className="t-caret"/></p>}
    {task.status==='cancelling'&&<p className="t-dim">正在停止本任务…</p>}
    {!!task.steps?.length&&<div className="t-output">
      {task.steps.map(step=><div className="t-step" key={step.step_index}>
        {plan?.steps[step.step_index]&&<pre className="t-command">{plan.steps[step.step_index].command}</pre>}
        {step.stdout&&<pre className="t-stdout">{step.stdout.replace(/\n$/,'')}</pre>}
        {step.stderr&&<pre className="t-stderr">{step.stderr.replace(/\n$/,'')}</pre>}
        {step.facts&&<div className="t-facts">
          <p>本机 {step.facts.port} 端口 · {step.facts.protocol} 监听</p>
          <p>{step.facts.listening?'发现可见监听进程':'当前用户可见范围未发现 TCP 监听'}</p>
          {step.facts.processes.map((p,i)=><p key={i}>　{p.process} · PID {p.pid} · {p.listeners.join('、')}</p>)}
          <p className="t-note">{step.facts.scope} · 查询无需联网</p>
        </div>}
        {step.error&&<p className="t-fail">✗ {step.error}</p>}
        {step.exit_code!==null&&step.exit_code!==undefined&&<p className={step.exit_code===0?'t-ok':'t-fail'}>{step.exit_code===0?'[exit 0]':'[exit '+step.exit_code+']'}</p>}
      </div>)}
    </div>}
    {task.error&&<p className="t-fail">✗ {task.error}</p>}
    {task.summary&&<div className="t-summary"><p className="t-ai"><span className="t-ainame">AI</span> 结果解释</p><p>{task.summary}</p></div>}
    {['failed','cancelled','interrupted','expired'].includes(task.status)&&<p className="t-actions"><button disabled={busy} onClick={onReplan}>按原需求重新规划</button></p>}
    {(plan||task.steps?.length)&&<details className="t-details"><summary>命令原始记录与环境</summary>
      <p className="t-note">状态 {terminalLabels[task.status]||task.status} · 计划 hash {(task.plan_hash||'').slice(0,16)}… · 确认 {task.confirmed_at?new Date(task.confirmed_at).toLocaleString():'未确认'}</p>
      <pre>{JSON.stringify({cwd:plan?.cwd,environment:plan?.environment,impact:plan?.impact},null,2)}</pre>
      <p className="t-note">原始输出与退出码为事实记录；AI 解释仅供参考，解释错误不影响原始结果。取消不回滚已发生的文件修改。</p>
    </details>}
  </article>;
}
