export interface Citation {
  document_id: string;
  document_title: string;
  chunk_id: string;
  heading?: string | null;
  snippet: string;
}
export interface StreamEvent {
  type: "meta" | "token" | "citation" | "done" | "error";
  conversation_id?: string;
  message_id?: number;
  model?: string;
  content?: string | null;
  citations?: Citation[] | null;
  error?: string | null;
}
export interface ModelList {
  llm: string;
  embedding: string;
  available: { name: string; size: number }[];
  status: "ready" | "unavailable";
  error?: string;
}
export interface Conversation {
  conversation_id: string;
  title: string;
  updated_at: string;
}
export interface SavedMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  status: string;
  model?: string;
  error?: string;
}
export interface DocumentMeta {
  document_id: string;
  title: string;
  source_path?: string | null;
  created_at: string;
  updated_at: string;
}
