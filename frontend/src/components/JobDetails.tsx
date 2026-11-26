import type { Job } from "../api/types";
import MessageBubble from "./MessageBubble";

export const jobLabels: Record<string, string> = {
  queued: "排队中", running: "执行中", cancelling: "正在取消", completed: "已完成",
  failed: "执行失败", cancelled: "已取消", interrupted: "服务中断",
};
const pending = new Set(["queued", "running", "cancelling"]);
export default function JobDetails({ job, busy, onAction }: {
  job: Job; busy: boolean; onAction: (kind: "cancel" | "retry") => void;
}) {
  return <>
    <h3>{job.instruction}</h3>
    <div className={`job-status ${job.status}`}>{jobLabels[job.status]} · {job.summary}</div>
    <p className="badge">{job.model} · 本机诊断{job.allow_diagnostics ? "已授权" : "未开启"}</p>
    {job.error && <p className="error" role="alert">{job.error}</p>}
    {pending.has(job.status) && <><p>后台正在处理，你可以离开此页面后再查看结果。</p>
      <button disabled={busy || job.status === "cancelling"} onClick={() => onAction("cancel")}>取消任务</button></>}
    {["failed", "cancelled", "interrupted"].includes(job.status) &&
      <button disabled={busy} onClick={() => onAction("retry")}>创建重试任务</button>}
    {job.result && <MessageBubble message={{ id: 0, role: "assistant", content: job.result,
      status: job.status === "completed" ? "complete" : "interrupted", model: job.model, citations: job.citations }} />}
    {!!job.events?.length && <details className="run-panel"><summary>执行明细 · {job.events.length} 个事件</summary>
      {job.events.map(event => <details key={event.seq}><summary>{event.seq}. {event.kind} {String(event.data.tool || "")}</summary>
        <pre>{JSON.stringify(event.data, null, 2)}</pre></details>)}
    </details>}
    <small>提交于 {new Date(job.created_at).toLocaleString()}</small>
  </>;
}
