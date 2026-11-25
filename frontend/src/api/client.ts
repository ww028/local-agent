import type { DocumentMeta } from "./types";

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export async function getModels(): Promise<{ llm: string; embedding: string }> {
  return parseJson(await fetch("/api/models"));
}

export async function listDocuments(): Promise<{ documents: DocumentMeta[] }> {
  return parseJson(await fetch("/api/documents"));
}

export async function uploadDocument(file: File): Promise<{ document_id: string }> {
  const form = new FormData();
  form.append("file", file);
  return parseJson(
    await fetch("/api/documents", { method: "POST", body: form }),
  );
}

export async function deleteDocument(documentId: string): Promise<void> {
  await fetch(`/api/documents/${documentId}`, { method: "DELETE" });
}
