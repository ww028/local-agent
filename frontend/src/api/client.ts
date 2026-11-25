import type { Conversation, DocumentMeta, DocumentPreview, ModelList, SavedMessage } from "./types";

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
export async function getModels(): Promise<ModelList> {
  return parseJson(await fetch("/api/models"));
}
export async function listChats(): Promise<{ conversations: Conversation[] }> {
  return parseJson(await fetch("/api/chats"));
}
export async function getChat(id: string): Promise<{ conversation: Conversation; messages: SavedMessage[] }> {
  return parseJson(await fetch(`/api/chats/${encodeURIComponent(id)}`));
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
