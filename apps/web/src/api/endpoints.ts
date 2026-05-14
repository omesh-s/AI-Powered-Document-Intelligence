import { apiRequest } from "@/lib/apiClient";

export type User = {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
};

export type Workspace = { id: string; name: string; slug: string; role: string; created_at: string };

export type Document = {
  id: string;
  workspace_id: string;
  filename: string;
  content_type: string;
  file_size: number;
  storage_key: string;
  status: string;
  latest_version_id: string | null;
  created_by: string | null;
  created_at: string;
  ingestion_job: {
    id: string;
    status: string;
    stage: string;
    progress: number;
  } | null;
};

export type DocumentListResponse = {
  items: Document[];
  pagination: { page: number; size: number; total: number };
};

export type IngestionJob = {
  id: string;
  document_id: string;
  document_version_id: string;
  status: string;
  stage: string;
  progress: number;
  attempts: number;
  started_at: string | null;
  finished_at: string | null;
  error_code: string | null;
  error_message: string | null;
};

export type IngestionJobDetail = {
  job: IngestionJob;
  document: {
    id: string;
    filename: string;
    content_type: string;
    status: string;
    workspace_id: string;
    created_at: string;
  };
  metrics: Record<string, unknown> | null;
};

export type QuerySessionItem = {
  id: string;
  workspace_id: string;
  document_id: string | null;
  title: string | null;
  created_at: string;
};

export type Citation = {
  document_id: string;
  document_name: string;
  document_version_id: string;
  page_number: number | null;
  chunk_id: string | null;
  excerpt: string;
  score: number;
};

export type QueryMessage = {
  id: string;
  role: string;
  content: string;
  answerability: string | null;
  created_at: string | null;
  citations: Citation[] | null;
  debug_json: Record<string, unknown> | null;
};

export type AskResponse = {
  session: { id: string; workspace_id: string; document_id: string | null };
  message: QueryMessage;
  citations: Citation[];
  debug: Record<string, unknown> | null;
};

export async function login(email: string, password: string) {
  return apiRequest<{ user: User; tokens: { access_token: string; refresh_token: string } }>(
    "/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }), auth: false },
  );
}

export async function register(email: string, password: string, full_name?: string) {
  return apiRequest<{ user: User; tokens: { access_token: string; refresh_token: string } }>(
    "/auth/register",
    { method: "POST", body: JSON.stringify({ email, password, full_name }), auth: false },
  );
}

export async function fetchMe() {
  return apiRequest<User>("/auth/me");
}

export async function fetchWorkspaces() {
  return apiRequest<Workspace[]>("/workspaces/");
}

export async function createWorkspace(name: string) {
  return apiRequest<Workspace>("/workspaces/", { method: "POST", body: JSON.stringify({ name }) });
}

export async function fetchDocuments(workspaceId: string, page: number, size: number, status?: string) {
  const q = new URLSearchParams({
    workspace_id: workspaceId,
    page: String(page),
    size: String(size),
  });
  if (status) q.set("status", status);
  return apiRequest<DocumentListResponse>(`/documents/?${q.toString()}`);
}

export async function fetchDocument(documentId: string) {
  return apiRequest<Document>(`/documents/${documentId}`);
}

export async function requestUploadUrl(body: {
  workspace_id: string;
  filename: string;
  content_type: string;
  file_size: number;
}) {
  return apiRequest<{
    storage_key: string;
    upload_url: string;
    expires_in_seconds: number;
    required_headers: Record<string, string>;
  }>("/documents/upload-url", { method: "POST", body: JSON.stringify(body) });
}

export async function finalizeDocument(body: {
  workspace_id: string;
  filename: string;
  content_type: string;
  file_size: number;
  storage_key: string;
  checksum_sha256?: string | null;
}) {
  return apiRequest<Document>("/documents/", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchDocumentPages(documentId: string) {
  return apiRequest<{
    document_id: string;
    document_version_id: string;
    pages: {
      id: string;
      page_number: number;
      extraction_method: string;
      markdown_text: string | null;
      raw_text: string | null;
    }[];
  }>(`/documents/${documentId}/pages`);
}

export async function fetchDocumentChunks(documentId: string) {
  return apiRequest<{
    document_id: string;
    document_version_id: string;
    chunks: {
      id: string;
      chunk_index: number;
      page_id: string | null;
      page_number: number | null;
      text: string;
      metadata_json: Record<string, unknown> | null;
      embedding_model: string | null;
    }[];
  }>(`/documents/${documentId}/chunks`);
}

export async function reprocessDocument(documentId: string) {
  return apiRequest<{ job: IngestionJob }>(`/documents/${documentId}/reprocess`, { method: "POST" });
}

export async function fetchIngestionJobs(params: {
  workspace_id?: string;
  document_id?: string;
  status?: string;
  page: number;
  size: number;
}) {
  const q = new URLSearchParams({
    page: String(params.page),
    size: String(params.size),
  });
  if (params.workspace_id) q.set("workspace_id", params.workspace_id);
  if (params.document_id) q.set("document_id", params.document_id);
  if (params.status) q.set("status", params.status);
  return apiRequest<{ items: IngestionJob[]; pagination: { page: number; size: number; total: number } }>(
    `/ingestion/jobs?${q.toString()}`,
  );
}

export async function fetchIngestionJob(jobId: string) {
  return apiRequest<IngestionJobDetail>(`/ingestion/jobs/${jobId}`);
}

export async function askQuery(body: {
  workspace_id: string;
  document_id?: string | null;
  session_id?: string | null;
  question: string;
  debug?: boolean;
}) {
  return apiRequest<AskResponse>("/query/ask", { method: "POST", body: JSON.stringify(body) });
}

export async function fetchSessions(workspaceId: string, page: number, size: number, documentId?: string) {
  const q = new URLSearchParams({ workspace_id: workspaceId, page: String(page), size: String(size) });
  if (documentId) q.set("document_id", documentId);
  return apiRequest<{ items: QuerySessionItem[]; pagination: { page: number; size: number; total: number } }>(
    `/query/sessions?${q.toString()}`,
  );
}

export async function fetchSession(sessionId: string) {
  return apiRequest<{ session: AskResponse["session"]; messages: QueryMessage[] }>(
    `/query/sessions/${sessionId}`,
  );
}
