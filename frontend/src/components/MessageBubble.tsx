import ReactMarkdown from "react-markdown";
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
      {message.status !== "complete" && <small className="status">{message.status}</small>}
      {message.error && <p role="alert" className="error">{message.error}</p>}
    </article>
  );
}
