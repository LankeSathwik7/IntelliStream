const API_URL = "https://darkhorse09-intellistream.hf.space";

export interface HistoryMessage {
  role: string;
  content: string;
}

export interface ChatRequest {
  message: string;
  thread_id?: string;
  sources?: string[];
  history?: HistoryMessage[];
}

export interface ChatResponse {
  response: string;
  thread_id: string;
  sources: Source[];
  agent_trace: AgentTrace[];
  latency_ms: number;
}

export interface Source {
  id: string;
  title: string;
  url?: string;
  snippet: string;
  score: number;
}

export interface AgentTrace {
  agent: string;
  action: string;
  latency_ms: number;
  [key: string]: unknown;
}

export interface StreamEvent {
  type: "agent_status" | "response" | "token" | "done" | "error";
  data?: {
    agent?: string;
    status?: string;
    content?: string;
    sources?: Source[];
    thread_id?: string;
    message?: string;
  };
}

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_URL}/api/chat/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

export async function* streamChatMessage(
  request: ChatRequest
): AsyncGenerator<StreamEvent, void, unknown> {
  const response = await fetch(`${API_URL}/api/chat/stream/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event: StreamEvent = JSON.parse(line.slice(6));
          yield event;
        } catch {
          // Ignore parse errors
        }
      }
    }
  }
}

export async function checkHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_URL}/health`);
  return response.json();
}

export interface ExportPDFRequest {
  messages: Array<{
    role: string;
    content: string;
    sources?: Source[];
  }>;
  title?: string;
  include_sources?: boolean;
}

export async function exportToPDF(request: ExportPDFRequest): Promise<Blob> {
  const response = await fetch(`${API_URL}/api/chat/export/pdf`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Export failed" }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.blob();
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export interface UploadDocumentResponse {
  document_id?: string;
  filename: string;
  chunk_count: number;
  message?: string;
  status?: string;
  format?: string;
  title?: string;
}

export async function uploadDocument(
  file: File,
  signal?: AbortSignal
): Promise<UploadDocumentResponse> {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${API_URL}/api/documents/upload`, {
      method: "POST",
      body: formData,
      ...(signal ? { signal } : {}),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    return {
      ...data,
      chunk_count: data.chunks_created || data.chunk_count || 1,
    };
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("Upload was cancelled");
    }
    throw err;
  }
}

export interface ImageAnalysisResponse {
  status: string;
  filename: string;
  analysis: string;
  format: string;
}

export async function analyzeImage(file: File, prompt?: string): Promise<ImageAnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (prompt) {
    formData.append("prompt", prompt);
  }

  const response = await fetch(`${API_URL}/api/documents/analyze-image`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Image analysis failed" }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// ==================
// SETTINGS API
// ==================

export interface UserSettings {
  theme: "light" | "dark" | "system";
  soundEnabled: boolean;
  notificationsEnabled: boolean;
  streamingSpeed: "slow" | "medium" | "fast";
}

export interface SettingsResponse {
  success: boolean;
  settings: UserSettings | null;
  message?: string;
}

export async function getSettings(accessToken?: string): Promise<SettingsResponse> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_URL}/api/settings/`, {
    method: "GET",
    headers,
  });

  if (!response.ok) {
    return {
      success: false,
      settings: null,
      message: "Failed to load settings",
    };
  }

  return response.json();
}

export async function saveSettings(
  settings: UserSettings,
  accessToken: string
): Promise<SettingsResponse> {
  const response = await fetch(`${API_URL}/api/settings/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${accessToken}`,
    },
    body: JSON.stringify(settings),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to save settings" }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}
