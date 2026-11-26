import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { TerminalTask } from "../api/types";

export const terminalLabels:Record<string,string>={planning:"AI 生成命令中",awaiting_confirmation:"等待确认",queued:"准备执行",running:"执行中",cancelling:"正在停止",completed:"已结束",failed:"失败",cancelled:"已取消",interrupted:"服务中断",expired:"确认已过期"};

const COMMANDS='查看即将执行的命令';

/** Short result prose: GFM only, no images/links, so stray Markdown never shows as raw symbols. */
function Markdown({text}:{text:string}){
  return <div className="t-explain"><ReactMarkdown skipHtml remarkPlugins={[remarkGfm]} components={{
    img:({alt})=><span>[图片未加载：{alt}]</span>,a:({children})=><span>{children}</span>,
  }}>{text}</ReactMarkdown></div>;
}

/** One dialogue turn in the console: your request → key result → folded command/output details. */
export default function TerminalEntry({task,busy,onConfirm,onCancel,onReplan}:{task:TerminalTask;busy:boolean;onConfirm:()=>void;onCancel:()=>void;onReplan:()=>void}){
  const plan=task.plan;
  const pending=task.status==='awaiting_confirmation';
  const effects=plan?.effects?.length?plan.effects:[plan?.impact].filter(Boolean) as string[];
  const rawOutputs=(task.steps||[]).filter(step=>step.stdout||step.stderr||step.error);
  const digest=task.digest;
  const result=digest||(task.status==='completed'?task.summary:undefined);
  const explain=task.digest&&task.summary&&task.summary!==task.digest?task.summary:undefined;
  return <article className="t-entry">
    <div className="t-row user">
      <p className="t-bubble user">{task.instruction}</p>
      <span className="t-avatar me">你</span>
    </div>
    <div className="t-row ai">
      <span className="t-avatar ai">AI</span>
      <div className="t-ai-body">
        {task.status==='planning'&&<p className="t-dim">正在理解需求并生成命令…<span className="t-caret"/></p>}
        {plan&&<p className="t-goal">{plan.goal}</p>}
        {plan?.auto_run&&<p className="t-auto"><span className="t-chip">只读查询 · 已自动执行</span><span className="t-dim">只读取信息，不改动文件或系统设置，所以没有让你再确认。</span></p>}
        {digest&&<div className="t-result"><p className="t-result-label">结果</p><p className="t-result-text">{digest}</p>{explain&&<Markdown text={explain}/>}</div>}
        {!digest&&!!result&&<div className="t-result"><p className="t-result-label">结果</p><Markdown text={result}/></div>}
        {task.status==='queued'&&<p className="t-dim">等待执行…</p>}
        {task.status==='running'&&<p className="t-dim">执行中…<span className="t-caret"/></p>}
        {task.status==='cancelling'&&<p className="t-dim">正在停止本任务…</p>}
        {!!(task.steps||[]).length&&<div className="t-facts-list">
          {task.steps!.map(step=>step.facts&&<div className="t-facts" key={'f'+step.step_index}>
            <p>本机 {step.facts.port} 端口 · {step.facts.protocol} 监听</p>
            <p>{step.facts.listening?'发现可见监听进程':'当前用户可见范围未发现 TCP 监听'}</p>
            {step.facts.processes.map((p,i)=><p key={i}>　{p.process} · PID {p.pid} · {p.listeners.join('、')}</p>)}
          </div>)}
        </div>}
        {pending&&<div className="t-confirm">
          <p className="t-confirm-title">需要你确认后才执行</p>
          <p className="t-confirm-lead">执行后会有这些影响：</p>
          <ul className="t-effects">{effects.map((e,i)=><li key={i}>{e}</li>)}</ul>
          <div className="t-confirm-actions">
            <button className="primary" disabled={busy} onClick={()=>onConfirm()}>执行 (y)</button>
            <button disabled={busy} onClick={()=>onCancel()}>取消 (n)</button>
          </div>
          <p className="t-note">也可以直接在下方输入 <kbd>y</kbd> 或 <kbd>n</kbd> 回车。确认只对应这份命令，{new Date(task.expires_at||'').toLocaleTimeString()} 前有效。</p>
        </div>}
        {task.error&&<p className="t-fail">✗ {task.error}</p>}
        {!!rawOutputs.length&&<details className="t-details">
          <summary>查看原始输出</summary>
          <div className="t-output">
            {task.steps!.map(step=><div className="t-step" key={step.step_index}>
              {step.stdout&&<pre className="t-stdout">{step.stdout.replace(/\n$/,'')}</pre>}
              {step.stderr&&<pre className="t-stderr">{step.stderr.replace(/\n$/,'')}</pre>}
              {step.error&&<p className="t-fail">✗ {step.error}</p>}
              {step.exit_code!==null&&step.exit_code!==undefined&&<p className={step.exit_code===0?'t-ok':'t-fail'}>{step.exit_code===0?'[exit 0]':'[exit '+step.exit_code+']'}</p>}
            </div>)}
          </div>
        </details>}
        {!!plan?.steps.length&&<details className="t-details">
          <summary>{COMMANDS}</summary>
          <div className="t-commands">
            {plan.steps.map((step,index)=><div className="t-cmd" key={index}>
              <p className="t-dim">{plan.steps.length>1?`${index+1}. `:''}{step.description}</p>
              <pre className="t-command">{step.command}</pre>
            </div>)}
          </div>
        </details>}
        {(plan||task.steps?.length)&&<details className="t-details"><summary>技术记录</summary>
          <p className="t-note">状态 {terminalLabels[task.status]||task.status} · 计划 hash {(task.plan_hash||'').slice(0,16)}… · 确认 {task.confirmed_at?new Date(task.confirmed_at).toLocaleString():plan?.auto_run?'只读自动执行':'未确认'}</p>
          {plan?.warnings?.map((w,i)=><p className="t-note" key={i}>{w}</p>)}
          <pre>{JSON.stringify({cwd:plan?.cwd,environment:plan?.environment,impact:plan?.impact,effects:plan?.effects},null,2)}</pre>
          <p className="t-note">原始输出与退出码为事实记录。取消不回滚已发生的文件修改。</p>
        </details>}
        {['failed','cancelled','interrupted','expired'].includes(task.status)&&<p className="t-actions"><button disabled={busy} onClick={()=>onReplan()}>按原需求重新规划</button></p>}
      </div>
    </div>
  </article>;
}
