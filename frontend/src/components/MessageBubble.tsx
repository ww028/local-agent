import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Link } from "react-router-dom";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeHighlight from "rehype-highlight";
import "katex/dist/katex.min.css";
import "highlight.js/styles/github.css";
import RunDetails from "./RunDetails";
import type { SavedMessage } from "../api/types";

const statuses:Record<string,string>={generating:"生成中",interrupted:"已停止",error:"失败"};
export default function MessageBubble({ message }: { message: SavedMessage }) {
  const [copied,setCopied]=useState(false);
  return <article className={`bubble ${message.role}`}>
    <div className="message-label"><span>{message.role==="user"?"你":message.model||"助手"}</span>
      <button onClick={()=>void navigator.clipboard.writeText(message.content).then(()=>{setCopied(true);setTimeout(()=>setCopied(false),1500);}).catch(()=>setCopied(false))}>{copied?"已复制":"复制"}</button>
    </div>
    <ReactMarkdown skipHtml remarkPlugins={[remarkGfm,remarkMath]} rehypePlugins={[[rehypeKatex,{trust:false,maxExpand:1000}], [rehypeHighlight,{ignoreMissing:true}]]} components={{
      img:({alt})=><span>[图片未联网加载：{alt}]</span>,a:({children})=><span>{children}</span>,
    }}>{message.content||(message.status==="generating"?"等待本地模型…":"")}</ReactMarkdown>
    {message.citations&&message.citations.length>0&&<details className="citation-list"><summary>检索来源 · {message.citations.length} 个片段（以回答标号为准）</summary>{message.citations.map((c,i)=><div key={c.chunk_id}><Link to={`/documents?id=${c.document_id}&chunk=${encodeURIComponent(c.chunk_id)}`}>[{i+1}] {c.document_title} · {c.heading}</Link><p>{c.snippet}</p></div>)}</details>}
    {message.run_id&&<RunDetails id={message.run_id}/>}
    {message.status!=="complete"&&<small className="status">{statuses[message.status]||message.status}</small>}
    {message.error&&<p role="alert" className="error">{message.error}</p>}
  </article>;
}
