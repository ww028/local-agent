import type { Conversation, DocumentMeta, DocumentPreview, ModelList, SavedMessage, Job } from "./types";

export async function responseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`;
  } catch { return `Request failed (${res.status})`; }
}
async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(await responseError(res));
  return res.json() as Promise<T>;
}
export async function listJobs(offset=0): Promise<{jobs:Job[]}> {
  return parseJson(await fetch(`/api/jobs?limit=50&offset=${offset}`));
}
export async function getJob(id:string): Promise<Job> {
  return parseJson(await fetch(`/api/jobs/${encodeURIComponent(id)}`));
}
export async function submitJob(instruction:string,model:string,allow_diagnostics:boolean): Promise<Job> {
  return parseJson(await fetch('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({instruction,model,allow_diagnostics})}));
}
export async function cancelJob(id:string): Promise<Job> {
  return parseJson(await fetch(`/api/jobs/${encodeURIComponent(id)}/cancel`,{method:'POST'}));
}
export async function retryJob(id:string): Promise<Job> {
  return parseJson(await fetch(`/api/jobs/${encodeURIComponent(id)}/retry`,{method:'POST'}));
}

export async function getModels(): Promise<ModelList> {
  return parseJson(await fetch("/api/models"));
}
export async function listChats(): Promise<{ conversations: Conversation[] }> {
  return parseJson(await fetch("/api/chats"));
}
export async function getChat(id: string): Promise<{ conversation: Conversation; messages: SavedMessage[] }> {
  return parseJson(await fetch(`/api/chats/${encodeURIComponent(id)}`));
}
export async function renameChat(id: string,title: string): Promise<void> {
  await parseJson(await fetch(`/api/chats/${encodeURIComponent(id)}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({title})}));
}
export async function deleteChat(id: string): Promise<void> {
  await parseJson(await fetch(`/api/chats/${encodeURIComponent(id)}`, { method: "DELETE" }));
}
export async function listDocuments(): Promise<{ documents: DocumentMeta[] }> {
  return parseJson(await fetch("/api/documents"));
}
export async function uploadDocument(file: File): Promise<{ document_id: string }> {
  const form = new FormData();
  form.append("file", file);
  return parseJson(await fetch("/api/documents", { method: "POST", body: form }));
}
export async function getDocument(id: string): Promise<DocumentPreview> {
  return parseJson(await fetch(`/api/documents/${encodeURIComponent(id)}`));
}
export async function reindexDocument(id: string): Promise<void> {
  await parseJson(await fetch(`/api/documents/${encodeURIComponent(id)}/reindex`, { method: "POST" }));
}
export async function deleteDocument(id: string): Promise<void> {
  await parseJson(await fetch(`/api/documents/${encodeURIComponent(id)}`, { method: "DELETE" }));
}
