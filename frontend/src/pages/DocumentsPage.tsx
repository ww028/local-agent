import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { deleteDocument, getDocument, listDocuments, reindexDocument, uploadDocument } from "../api/client";
import type { DocumentMeta, DocumentPreview } from "../api/types";

const labels: Record<string,string> = { pending:"待索引", indexing:"索引中", ready:"可检索", error:"索引失败", deleting:"删除中" };
export default function DocumentsPage() {
  const [documents,setDocuments]=useState<DocumentMeta[]>([]);
  const [preview,setPreview]=useState<DocumentPreview|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [params]=useSearchParams();
  const refresh=useCallback(async()=>{ setDocuments((await listDocuments()).documents); },[]);
  const open=useCallback(async(id:string)=>{ try { setPreview(await getDocument(id));setError(""); } catch(e){setError(e instanceof Error?e.message:"预览失败");} },[]);
  useEffect(()=>{ void refresh().catch(e=>setError(e.message));const timer=setInterval(()=>void refresh().catch(()=>undefined),2000);return()=>clearInterval(timer); },[refresh]);
  useEffect(()=>{ const id=params.get("id");if(id) void open(id); },[params,open]);
  useEffect(()=>{ if(preview&&params.get("chunk"))document.getElementById(params.get("chunk")!)?.scrollIntoView({block:"center"}); },[preview,params]);
  const upload=async(files:FileList|null)=>{
    if(!files)return;setBusy(true);setError("");
    try { for(const file of Array.from(files)) await uploadDocument(file);await refresh(); }
    catch(e){setError(e instanceof Error?e.message:"上传失败");}finally{setBusy(false);}
  };
  const remove=async(id:string)=>{ if(!confirm("删除此文档和检索索引？"))return;try{await deleteDocument(id);if(preview?.document.document_id===id)setPreview(null);await refresh();}catch(e){setError(e instanceof Error?e.message:"删除失败");} };
  return <div className="knowledge-page">
    <header><h2>本地知识库</h2><p>Markdown / TXT · 文件不出本机 · 单文件最大 4 MB</p></header>
    {error&&<p className="error" role="alert">{error}</p>}
    <div className="knowledge-layout">
      <section className="document-list">
        <label className="upload-zone">{busy?"上传中…":"＋ 导入文档"}<input aria-label="导入文档" type="file" multiple accept=".md,.markdown,.txt" disabled={busy} onChange={e=>{void upload(e.target.files);e.target.value="";}} /></label>
        {!documents.length&&<p className="empty">导入资料后即可在对话中开启知识库问答。</p>}
        {documents.map(doc=><article className="document-item" key={doc.document_id}>
          <button onClick={()=>void open(doc.document_id)}>{doc.title}</button>
          <p><span className={`badge ${doc.status}`}>{labels[doc.status]||doc.status}</span> · {doc.indexed_chunks}/{doc.chunk_count} 片段</p>
          {doc.error&&<p className="error">{doc.error}</p>}
          <div><button disabled={doc.status==="indexing"||doc.status==="pending"} onClick={()=>void reindexDocument(doc.document_id).then(refresh).catch(e=>setError(e.message))}>重建索引</button> <button onClick={()=>void remove(doc.document_id)}>删除</button></div>
        </article>)}
      </section>
      <section className="document-preview">
        {preview?<><h3>{preview.document.title}</h3><details><summary>查看完整原文</summary><pre className="source-text">{preview.content}</pre></details>
          {preview.chunks.map(chunk=><article key={chunk.chunk_id} id={chunk.chunk_id} className={`source-chunk ${params.get("chunk")===chunk.chunk_id?"highlighted":""}`}>
            <h4>{chunk.heading||"正文"} <small>行 {chunk.start_line}–{chunk.end_line}</small></h4><pre className="source-text">{chunk.text}</pre>
          </article>)}</>:<div className="empty"><h3>原文与来源</h3><p>选择文档查看结构片段；对话的引用可跳回这里。</p></div>}
      </section>
    </div>
  </div>;
}
