"use client";

import { useState, useCallback, useRef } from "react";
import { FileText, Image as ImageIcon, X, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import { AgentStatusDisplay } from "./AgentStatusDisplay";
import { WelcomeScreen } from "./WelcomeScreen";
import { uploadDocument, analyzeImage } from "@/lib/api";
import type { useChat } from "@/hooks/useChat";
import type { Attachment } from "@/types";

interface PendingAttachment {
  id: string;
  file: File;
  type: "image" | "pdf" | "document";
  previewUrl?: string;
  status: "uploading" | "processing" | "ready" | "error" | "analyzing";
  progress: number;
  error?: string;
  result?: {
    filename?: string;
    chunkCount?: number;
    analysis?: string;
  };
  abortController?: AbortController;
}

interface UploadedDoc {
  filename: string;
  chunkCount: number;
  uploadedAt: Date;
}

interface ChatInterfaceProps {
  chat: ReturnType<typeof useChat>;
}

export function ChatInterface({ chat }: ChatInterfaceProps) {
  const {
    messages,
    isLoading,
    error,
    agentStatus,
    sendMessage: sendRawMessage,
    sendMessageWithAttachments,
    editMessage,
    navigateVersion,
  } = chat;

  const [uploadedDocs, setUploadedDocs] = useState<UploadedDoc[]>([]);
  const [pendingAttachments, setPendingAttachments] = useState<PendingAttachment[]>([]);

  // Start uploading immediately when file is selected
  const handleFileSelect = useCallback(async (file: File) => {
    const isImage = file.type.startsWith("image/");
    const isPdf = file.type === "application/pdf";
    const abortController = new AbortController();

    const attachment: PendingAttachment = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      file,
      type: isImage ? "image" : isPdf ? "pdf" : "document",
      status: isImage ? "analyzing" : "uploading",
      progress: 0,
      abortController,
    };

    // Create preview URL for images
    if (isImage) {
      attachment.previewUrl = URL.createObjectURL(file);
    }

    setPendingAttachments((prev) => [...prev, attachment]);

    // Start upload/analysis immediately
    try {
      if (isImage) {
        // Analyze image
        const result = await analyzeImage(file);
        setPendingAttachments((prev) =>
          prev.map((a) =>
            a.id === attachment.id
              ? { ...a, status: "ready", progress: 100, result: { analysis: result.analysis } }
              : a
          )
        );
      } else {
        // Upload document with progress simulation
        const progressInterval = setInterval(() => {
          setPendingAttachments((prev) =>
            prev.map((a) => {
              if (a.id !== attachment.id) return a;
              if (a.status === "uploading" && a.progress < 85) {
                return { ...a, progress: Math.min(a.progress + 10, 85) };
              }
              // After 85%, switch to processing state
              if (a.status === "uploading" && a.progress >= 85) {
                return { ...a, status: "processing", progress: 85 };
              }
              return a;
            })
          );
        }, 500);

        const result = await uploadDocument(file, abortController.signal);
        clearInterval(progressInterval);

        // Set to 100%
        setPendingAttachments((prev) =>
          prev.map((a) =>
            a.id === attachment.id ? { ...a, status: "uploading", progress: 100 } : a
          )
        );

        // Add to uploaded docs
        setUploadedDocs((prev) => [...prev, {
          filename: result.filename,
          chunkCount: result.chunk_count,
          uploadedAt: new Date(),
        }]);

        setPendingAttachments((prev) =>
          prev.map((a) =>
            a.id === attachment.id
              ? {
                  ...a,
                  status: "ready",
                  progress: 100,
                  result: { filename: result.filename, chunkCount: result.chunk_count },
                }
              : a
          )
        );
      }
    } catch (err) {
      if (abortController.signal.aborted) return;
      const message = err instanceof Error ? err.message : "Failed";
      setPendingAttachments((prev) =>
        prev.map((a) =>
          a.id === attachment.id ? { ...a, status: "error", error: message } : a
        )
      );
    }
  }, []);

  // Remove/cancel a pending attachment
  const removePendingAttachment = useCallback((id: string) => {
    setPendingAttachments((prev) => {
      const attachment = prev.find((a) => a.id === id);
      if (attachment) {
        // Cancel ongoing upload
        attachment.abortController?.abort();
        // Revoke preview URL
        if (attachment.previewUrl) {
          URL.revokeObjectURL(attachment.previewUrl);
        }
      }
      return prev.filter((a) => a.id !== id);
    });
  }, []);

  // Send message with ready attachments
  const sendMessage = useCallback(async (content: string) => {
    // Only include ready attachments
    const readyAttachments = pendingAttachments.filter((pa) => pa.status === "ready");

    const attachments: Attachment[] = readyAttachments.map((pa) => ({
      type: pa.type,
      name: pa.file.name,
      url: pa.previewUrl,
      size: pa.file.size,
    }));

    // Build context for the message
    let finalContent = content;
    const contextParts: string[] = [];

    for (const pa of readyAttachments) {
      if (pa.type === "image" && pa.result?.analysis) {
        contextParts.push(`[Image: ${pa.file.name}]\nAnalysis: ${pa.result.analysis}`);
      } else if (pa.result?.filename) {
        contextParts.push(`[Document: ${pa.file.name}] Search for relevant content from this document.`);
      }
    }

    // Clear pending attachments
    setPendingAttachments([]);

    // Add context to message
    if (contextParts.length > 0) {
      finalContent = contextParts.join("\n\n") + "\n\n" + content;
    } else if (uploadedDocs.length > 0 && !content.startsWith("[Context:")) {
      const docNames = uploadedDocs.map((d) => d.filename).join(", ");
      finalContent = `[Context: Documents available: ${docNames}]\n\n${content}`;
    }

    // Send message with attachments visually
    if (sendMessageWithAttachments && attachments.length > 0) {
      sendMessageWithAttachments(finalContent, attachments);
    } else {
      sendRawMessage(finalContent);
    }
  }, [pendingAttachments, uploadedDocs, sendRawMessage, sendMessageWithAttachments]);

  // File upload handlers
  const handleFileUpload = useCallback((file: File) => {
    handleFileSelect(file);
  }, [handleFileSelect]);

  const handleImageUpload = useCallback((file: File) => {
    handleFileSelect(file);
  }, [handleFileSelect]);

  const removeUploadedDoc = useCallback((filename: string) => {
    setUploadedDocs((prev) => prev.filter((doc) => doc.filename !== filename));
  }, []);

  // Check if any uploads are in progress
  const isUploading = pendingAttachments.some(
    (a) => a.status === "uploading" || a.status === "analyzing" || a.status === "processing"
  );

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Agent Status (shown when loading) */}
      {isLoading && (
        <div className="shrink-0 border-b border-border bg-card/50 px-4 py-2">
          <AgentStatusDisplay status={agentStatus} />
        </div>
      )}

      {/* Uploaded Documents Context */}
      {uploadedDocs.length > 0 && (
        <div className="shrink-0 border-b border-border bg-primary/5 px-4 py-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-medium text-muted-foreground">
              Documents in context:
            </span>
            {uploadedDocs.map((doc) => (
              <div
                key={doc.filename}
                className="flex items-center gap-1 rounded-full bg-primary/10 px-2 py-1 text-xs"
              >
                <FileText className="h-3 w-3 text-primary" />
                <span className="text-primary font-medium">{doc.filename}</span>
                <span className="text-muted-foreground">({doc.chunkCount} chunks)</span>
                <button
                  onClick={() => removeUploadedDoc(doc.filename)}
                  className="ml-1 rounded-full p-0.5 hover:bg-primary/20"
                  title="Remove from context display"
                >
                  <X className="h-3 w-3 text-muted-foreground" />
                </button>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Ask questions about your uploaded documents - sources will be shown in responses
          </p>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto flex flex-col">
        {messages.length === 0 ? (
          <WelcomeScreen onExampleClick={sendMessage} />
        ) : (
          <MessageList messages={messages} isLoading={isLoading} onEditMessage={editMessage} onNavigateVersion={navigateVersion} />
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="shrink-0 mx-4 mb-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Pending Attachments Preview */}
      {pendingAttachments.length > 0 && (
        <div className="shrink-0 mx-4 mb-2 flex flex-wrap gap-3">
          {pendingAttachments.map((attachment) => (
            <div
              key={attachment.id}
              className="relative group rounded-lg border border-border bg-card overflow-hidden shadow-sm"
            >
              {attachment.type === "image" && attachment.previewUrl ? (
                <div className="w-24 h-24 relative">
                  <img
                    src={attachment.previewUrl}
                    alt={attachment.file.name}
                    className={`w-full h-full object-cover ${attachment.status !== "ready" ? "opacity-50" : ""}`}
                  />
                  {/* Progress overlay for images */}
                  {attachment.status === "analyzing" && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                      <div className="text-center text-white">
                        <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                        <span className="text-xs mt-1 block">Analyzing...</span>
                      </div>
                    </div>
                  )}
                  {/* Ready checkmark */}
                  {attachment.status === "ready" && (
                    <div className="absolute bottom-1 left-1 p-0.5 rounded-full bg-green-500">
                      <CheckCircle className="h-3 w-3 text-white" />
                    </div>
                  )}
                </div>
              ) : (
                <div className="w-48 p-3 flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-primary/10">
                      <FileText className="h-6 w-6 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{attachment.file.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {(attachment.file.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>
                  {/* Progress bar */}
                  {attachment.status === "uploading" && (
                    <div className="w-full">
                      <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                        <span>Uploading...</span>
                        <span>{attachment.progress}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all duration-300"
                          style={{ width: `${attachment.progress}%` }}
                        />
                      </div>
                    </div>
                  )}
                  {/* Processing state - after upload, waiting for embedding */}
                  {attachment.status === "processing" && (
                    <div className="flex items-center gap-2 text-xs text-primary">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      <span>Processing & indexing... (this may take a minute)</span>
                    </div>
                  )}
                  {/* Ready state */}
                  {attachment.status === "ready" && (
                    <div className="flex items-center gap-1 text-xs text-green-600">
                      <CheckCircle className="h-3 w-3" />
                      <span>Ready ({attachment.result?.chunkCount} chunks)</span>
                    </div>
                  )}
                  {/* Error state */}
                  {attachment.status === "error" && (
                    <div className="flex items-center gap-1 text-xs text-destructive">
                      <AlertCircle className="h-3 w-3" />
                      <span className="truncate">{attachment.error}</span>
                    </div>
                  )}
                </div>
              )}
              {/* Remove button */}
              <button
                onClick={() => removePendingAttachment(attachment.id)}
                className="absolute top-1 right-1 p-1 rounded-full bg-background/90 hover:bg-destructive hover:text-destructive-foreground text-muted-foreground transition-colors"
                title={attachment.status === "uploading" ? "Cancel upload" : "Remove"}
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="shrink-0 border-t border-border p-4">
        <MessageInput
          onSend={sendMessage}
          isLoading={isLoading}
          isUploading={isUploading}
          onFileUpload={handleFileUpload}
          onImageUpload={handleImageUpload}
        />
      </div>
    </div>
  );
}
