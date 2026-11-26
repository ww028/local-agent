export interface Citation {
  document_id: string;
  document_title: string;
  chunk_id: string;
  heading?: string | null;
  snippet: string;
}
export interface StreamEvent {
  type: "meta" | "token" | "citation" | "step" | "done" | "error";
  run_id?: string;
  event?: { seq: number; kind: string; data: Record<string,unknown> };
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
  citations?: Citation[];
  run_id?: string;
}
export interface DocumentMeta {
  document_id: string;
  title: string;
  source_path?: string | null;
  status: string;
  error?: string | null;
  indexed_chunks: number;
  chunk_count: number;
  byte_size: number;
  created_at: string;
  updated_at: string;
}
export type JobStatus = "queued" | "running" | "cancelling" | "completed" | "failed" | "cancelled" | "interrupted";
export interface Job {
  job_id: string;
  instruction: string;
  model: string;
  allow_diagnostics: boolean;
  status: JobStatus;
  summary: string;
  result?: string;
  error?: string | null;
  run_id?: string | null;
  parent_job_id?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  events?: {seq:number;kind:string;data:Record<string,unknown>}[];
  citations?: Citation[];
}

export interface TerminalPlan {
  goal: string; cwd: string; relative_dir: string; impact: string;
  environment: Record<string,string>;
  steps: { action:string;description:string;executable:string;args:string[];command:string;timeout_seconds:number }[];
}
export interface TerminalTask {
  task_id:string;instruction:string;status:string;model?:string;relative_dir?:string;
  plan?:TerminalPlan|null;plan_hash?:string|null;expires_at?:string|null;confirmed_at?:string|null;
  error?:string|null;summary?:string;created_at:string;
  steps?:{step_index:number;status:string;stdout:string;stderr:string;exit_code:number|null;error?:string|null}[];
}

export interface DocumentPreview {
  document: DocumentMeta;
  content: string;
  chunks: { chunk_id: string; heading: string; text: string; start_line: number; end_line: number }[];
}
