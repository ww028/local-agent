export interface Citation {
  document_id: string;
  document_title: string;
  chunk_id: string;
  heading?: string | null;
  snippet: string;
}

export interface StreamEvent {
  type: "token" | "citation" | "done" | "error";
  content?: string | null;
  citations?: Citation[] | null;
  error?: string | null;
}

export interface DocumentMeta {
  document_id: string;
  title: string;
  source_path?: string | null;
  created_at: string;
  updated_at: string;
}
