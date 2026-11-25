import ReactMarkdown from "react-markdown";
import { Link } from "react-router-dom";
import RunDetails from "./RunDetails";
import type { SavedMessage } from "../api/types";

export default function MessageBubble({ message }: { message: SavedMessage }) {
  return (
    <article className={`bubble ${message.role}`}>
      <div className="message-label">{message.role === "user" ? "你" : message.model || "助手"}</div>
      <ReactMarkdown skipHtml components={{
        // Remote images in model output must not cause a network request.
        img: ({ alt }) => <span>[图片未加载：{alt}]</span>,
        a: ({ children }) => <span>{children}</span>,
      }}>{message.content || (message.status === "generating" ? "等待本地模型…" : "")}</ReactMarkdown>
      {message.citations && message.citations.length>0 && <details className="citation-list"><summary>检索来源 · {message.citations.length} 个片段（以回答标号为准）</summary>{message.citations.map((c,i)=><div key={c.chunk_id}><Link to={`/documents?id=${c.document_id}&chunk=${encodeURIComponent(c.chunk_id)}`}>[{i+1}] {c.document_title} · {c.heading}</Link><p>{c.snippet}</p></div>)}</details>}
      {message.run_id && <RunDetails id={message.run_id} />}
      {message.status !== "complete" && <small className="status">{message.status}</small>}
      {message.error && <p role="alert" className="error">{message.error}</p>}
    </article>
  );
}
