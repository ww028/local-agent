import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { StaticRouter } from "react-router-dom";
import type { Job } from "../api/types";
import JobDetails from "./JobDetails";

const base: Job = { job_id: "synthetic", instruction: "Demo", model: "local", allow_diagnostics: false,
  status: "queued", summary: "等待", created_at: "2026-01-01T00:00:00Z" };
function render(changes: Partial<Job> = {}) {
  return renderToStaticMarkup(<StaticRouter location="/jobs"><JobDetails job={{ ...base, ...changes }} busy={false} onAction={() => {}} /></StaticRouter>);
}
describe("background job result presentation", () => {
  it("offers cancellation only while queued or running", () => {
    expect(render()).toContain("取消任务");
    expect(render({ status: "running" })).toContain("取消任务");
    expect(render({ status: "cancelling" })).toContain('disabled=""');
    expect(render({ status: "completed", result: "Done" })).not.toContain("取消任务");
  });
  it("shows failures and explicit retry without a fake result", () => {
    const html = render({ status: "failed", error: "Model unavailable" });
    expect(html).toContain("创建重试任务");
    expect(html).toContain('role="alert"');
    expect(html).not.toContain('class="bubble');
  });
  it("keeps model results separate from collapsed tool facts", () => {
    const html = render({ status: "completed", result: "Result from model", events: [
      { seq: 1, kind: "tool_result", data: { tool: "check_port", output: "fixed tool fact" } },
    ] });
    expect(html).toContain("Result from model");
    expect(html).toContain("fixed tool fact");
    expect(html).toContain('<details class="run-panel">');
    expect(html).not.toContain(" open");
  });
  it("retains evidence links while blocking raw HTML and remote images", () => {
    const html = render({ status: "completed", result: '<script>bad</script>\n![remote](https://example.com/photo.png)\n\n[1]', citations: [
      { document_id: "fictional-doc", document_title: "Fictional", chunk_id: "chunk-1", snippet: "Synthetic evidence" },
    ] });
    expect(html).not.toContain("<script>");
    expect(html).not.toContain("<img");
    expect(html).toContain("/documents?id=fictional-doc");
    expect(html).toContain("Synthetic evidence");
  });
});
