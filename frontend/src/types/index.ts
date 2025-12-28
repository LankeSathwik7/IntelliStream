export interface Attachment {
  type: "image" | "pdf" | "document";
  name: string;
  url?: string;  // For images, this is a data URL or blob URL
  size?: number;
}

export interface MessageVersion {
  id: string;
  content: string;
  timestamp: Date;
  response?: {
    id: string;
    content: string;
    sources?: Source[];
    timestamp: Date;
  };
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: Source[];
  agentTrace?: AgentTrace[];
  attachments?: Attachment[];
  timestamp: Date;
  isStreaming?: boolean;
  // Branching support
  versions?: MessageVersion[];  // All versions of this message (for user messages)
  currentVersionIndex?: number; // Which version is currently shown
  parentMessageId?: string;     // For assistant messages, links to the user message
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
  status: "pending" | "running" | "completed" | "error";
  latency_ms?: number;
}

export interface Thread {
  id: string;
  title?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface AgentStatus {
  router: "pending" | "running" | "completed";
  research: "pending" | "running" | "completed";
  analysis: "pending" | "running" | "completed";
  synthesizer: "pending" | "running" | "completed";
  reflection: "pending" | "running" | "completed";
  response: "pending" | "running" | "completed";
}
