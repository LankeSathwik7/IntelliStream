"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { User, Bot, ExternalLink, Loader2, FileText, Volume2, VolumeX, Pencil, Check, X, RotateCcw, Image as ImageIcon, ArrowDown, ChevronLeft, ChevronRight } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import type { Message } from "@/types";

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  onEditMessage?: (messageId: string, newContent: string, resend?: boolean) => Promise<void>;
  onNavigateVersion?: (messageId: string, direction: "prev" | "next") => void;
}

export function MessageList({ messages, isLoading, onEditMessage, onNavigateVersion }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const lastMessageCountRef = useRef(messages.length);
  const userScrolledAwayRef = useRef(false);
  const lastContentRef = useRef("");

  // Calculate current content for streaming detection
  const currentContent = messages.map(m => m.content || "").join("");

  // Handle scroll events - detect when user scrolls away from bottom
  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;

    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;

    // User scrolled away from bottom
    if (distanceFromBottom > 150) {
      userScrolledAwayRef.current = true;
      setShowScrollButton(true);
    }
    // User is at or near bottom
    else if (distanceFromBottom < 30) {
      userScrolledAwayRef.current = false;
      setShowScrollButton(false);
    }
  }, []);

  // Manual scroll to bottom button
  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    userScrolledAwayRef.current = false;
    setShowScrollButton(false);
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, []);

  // Auto-scroll when USER sends a new message
  useEffect(() => {
    if (messages.length > lastMessageCountRef.current) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg?.role === "user") {
        // User sent a message - scroll to bottom and reset state
        userScrolledAwayRef.current = false;
        setShowScrollButton(false);
        requestAnimationFrame(() => {
          if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
          }
        });
      }
    }
    lastMessageCountRef.current = messages.length;
  }, [messages.length]);

  // Auto-scroll during streaming ONLY if user hasn't scrolled away
  useEffect(() => {
    // Only scroll if:
    // 1. Content changed (streaming)
    // 2. User hasn't scrolled away
    // 3. We're loading
    if (currentContent !== lastContentRef.current && !userScrolledAwayRef.current && isLoading) {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    }
    lastContentRef.current = currentContent;
  }, [currentContent, isLoading]);

  // Check if we have a pending assistant message (empty content, still loading)
  const hasPendingAssistant = messages.some(
    (msg) => msg.role === "assistant" && !msg.content && msg.isStreaming
  );

  // Filter out assistant messages with no content (they're still loading)
  const visibleMessages = messages.filter(
    (msg) => msg.role === "user" || (msg.role === "assistant" && msg.content)
  );

  return (
    <div className="relative h-full">
      <div ref={scrollRef} className="h-full overflow-y-auto px-4 py-6" onScroll={handleScroll}>
        <div className="mx-auto max-w-3xl space-y-6">
          {visibleMessages.map((message) => (
            <MessageBubble key={message.id} message={message} onEditMessage={onEditMessage} onNavigateVersion={onNavigateVersion} />
          ))}

          {/* Show thinking indicator when waiting for response */}
          {isLoading && hasPendingAssistant && (
            <div className="flex gap-3 animate-message-in">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
                <Bot className="h-4 w-4 text-secondary-foreground" />
              </div>
              <div className="flex items-center gap-2 rounded-lg bg-secondary px-4 py-3">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Thinking...</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Scroll to bottom button */}
      {showScrollButton && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2 rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90 transition-all z-50"
        >
          <ArrowDown className="h-4 w-4" />
          <span className="text-sm font-medium">Scroll to bottom</span>
        </button>
      )}
    </div>
  );
}

interface MessageBubbleProps {
  message: Message;
  onEditMessage?: (messageId: string, newContent: string, resend?: boolean) => Promise<void>;
  onNavigateVersion?: (messageId: string, direction: "prev" | "next") => void;
}

function MessageBubble({ message, onEditMessage, onNavigateVersion }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);

  // Check if source is from uploaded document
  const isDocumentSource = (title: string) => {
    const docPatterns = [
      /\(Part \d+\/\d+\)$/,  // Chunked documents
      /^PDF:|^Document:/i,   // PDF/Document prefix
      /\.pdf$/i,             // PDF extension
    ];
    return docPatterns.some(pattern => pattern.test(title)) || !title.startsWith('http');
  };

  // Text-to-Speech handler
  const handleSpeak = () => {
    if (!message.content || isUser) return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(message.content);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (isSpeaking) {
        window.speechSynthesis.cancel();
      }
    };
  }, [isSpeaking]);

  return (
    <div
      className={cn(
        "flex gap-3 animate-message-in",
        isUser && !isEditing && "flex-row-reverse"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary" : "bg-secondary"
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-primary-foreground" />
        ) : (
          <Bot className="h-4 w-4 text-secondary-foreground" />
        )}
      </div>

      {/* Content */}
      <div
        className={cn(
          "flex flex-col gap-2",
          isEditing ? "w-full max-w-[700px]" : "max-w-[80%]",
          isUser && !isEditing && "items-end"
        )}
      >
        <div
          className={cn(
            "rounded-lg px-4 py-2",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-secondary text-secondary-foreground",
            isEditing && "w-full"
          )}
        >
          {isUser ? (
            isEditing ? (
              <div className="flex flex-col gap-3 w-full" style={{ minWidth: "400px" }}>
                {/* Show attachments as preview during editing */}
                {message.attachments && message.attachments.length > 0 && (
                  <div className="flex flex-wrap gap-2 opacity-75">
                    {message.attachments.map((attachment, idx) => (
                      <div
                        key={idx}
                        className="rounded-xl overflow-hidden border-2 border-primary-foreground/20 bg-primary-foreground/5"
                      >
                        {attachment.type === "image" && attachment.url ? (
                          <div className="relative">
                            <img
                              src={attachment.url}
                              alt={attachment.name}
                              className="max-w-[200px] max-h-[120px] object-cover rounded-lg"
                            />
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 px-3 py-2">
                            <FileText className="h-4 w-4" />
                            <span className="text-xs truncate max-w-[120px]">{attachment.name}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                <textarea
                  ref={(el) => {
                    if (el) {
                      el.style.height = "auto";
                      el.style.height = Math.max(el.scrollHeight, 80) + "px";
                    }
                  }}
                  value={editContent}
                  onChange={(e) => {
                    setEditContent(e.target.value);
                    e.target.style.height = "auto";
                    e.target.style.height = Math.max(e.target.scrollHeight, 80) + "px";
                  }}
                  className="w-full p-3 rounded-lg bg-white/20 text-primary-foreground border border-white/40 focus:outline-none focus:ring-2 focus:ring-white/60 resize-none text-sm placeholder:text-primary-foreground/50"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === "Escape") {
                      setIsEditing(false);
                      setEditContent(message.content);
                    }
                  }}
                />
                <div className="flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => {
                      setIsEditing(false);
                      setEditContent(message.content);
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-black/20 hover:bg-black/30 text-white cursor-pointer transition-colors"
                  >
                    <X className="h-3.5 w-3.5" /> Cancel
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      if (onEditMessage && editContent.trim()) {
                        setIsEditing(false);
                        // Always resend to get new AI response
                        await onEditMessage(message.id, editContent, true);
                      }
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-white/40 hover:bg-white/50 text-white cursor-pointer transition-colors"
                  >
                    <Check className="h-3.5 w-3.5" /> Save & Send
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {/* Attachments - Claude-like display */}
                {message.attachments && message.attachments.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {message.attachments.map((attachment, idx) => (
                      <div
                        key={idx}
                        className="rounded-xl overflow-hidden border-2 border-primary-foreground/20 bg-primary-foreground/5"
                      >
                        {attachment.type === "image" && attachment.url ? (
                          <div className="relative">
                            <img
                              src={attachment.url}
                              alt={attachment.name}
                              className="max-w-[280px] max-h-[200px] object-cover rounded-lg"
                            />
                            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
                              <span className="text-xs text-white/90 truncate block">{attachment.name}</span>
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-center gap-3 px-4 py-3 min-w-[200px]">
                            <div className="p-2 rounded-lg bg-primary-foreground/10">
                              <FileText className="h-6 w-6" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">{attachment.name}</p>
                              <p className="text-xs opacity-70">
                                {attachment.size ? `${(attachment.size / 1024).toFixed(1)} KB` : "Document"}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {/* Text content - filter out context hints for display */}
                {message.content && (
                  <p className="whitespace-pre-wrap">
                    {message.content.replace(/^\[(?:Context|Image|Document):[\s\S]*?\](?:\n\n)?/g, "").trim() || message.content}
                  </p>
                )}
              </div>
            )
          ) : message.content ? (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          ) : null}
        </div>

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">Sources:</p>
            <div className="flex flex-wrap gap-2">
              {message.sources.map((source, index) => {
                const isDoc = isDocumentSource(source.title);
                return (
                  <a
                    key={index}
                    href={source.url || "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={cn(
                      "flex items-center gap-1 rounded-full px-2 py-1 text-xs transition-colors",
                      isDoc
                        ? "bg-primary/10 text-primary hover:bg-primary/20"
                        : "bg-muted text-muted-foreground hover:text-foreground"
                    )}
                    title={source.snippet}
                  >
                    {isDoc ? (
                      <FileText className="h-3 w-3" />
                    ) : (
                      <ExternalLink className="h-3 w-3" />
                    )}
                    <span className="max-w-[150px] truncate">{source.title}</span>
                    {isDoc && (
                      <span className="ml-1 rounded bg-primary/20 px-1 text-[10px] font-medium">
                        DOC
                      </span>
                    )}
                  </a>
                );
              })}
            </div>
          </div>
        )}

        {/* Actions and Timestamp */}
        <div className="flex items-center gap-2">
          {/* Version Navigation for user messages with multiple versions */}
          {isUser && message.versions && message.versions.length > 1 && onNavigateVersion && (
            <div className="flex items-center gap-1 mr-2">
              <button
                onClick={() => onNavigateVersion(message.id, "prev")}
                disabled={(message.currentVersionIndex ?? message.versions!.length - 1) === 0}
                className={cn(
                  "p-1 rounded-full transition-colors",
                  (message.currentVersionIndex ?? message.versions!.length - 1) === 0
                    ? "text-muted-foreground/30 cursor-not-allowed"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                )}
                title="Previous version"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-xs text-muted-foreground min-w-[40px] text-center">
                {(message.currentVersionIndex ?? message.versions!.length - 1) + 1} / {message.versions!.length}
              </span>
              <button
                onClick={() => onNavigateVersion(message.id, "next")}
                disabled={(message.currentVersionIndex ?? message.versions!.length - 1) === message.versions!.length - 1}
                className={cn(
                  "p-1 rounded-full transition-colors",
                  (message.currentVersionIndex ?? message.versions!.length - 1) === message.versions!.length - 1
                    ? "text-muted-foreground/30 cursor-not-allowed"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                )}
                title="Next version"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
          {/* Edit Button for user messages */}
          {isUser && !isEditing && onEditMessage && (
            <button
              onClick={() => {
                setEditContent(message.content);
                setIsEditing(true);
              }}
              className="p-1 rounded-full transition-colors text-muted-foreground hover:text-foreground hover:bg-muted"
              title="Edit message"
            >
              <Pencil className="h-3 w-3" />
            </button>
          )}
          {/* TTS Button for assistant messages */}
          {!isUser && message.content && (
            <button
              onClick={handleSpeak}
              className={cn(
                "p-1 rounded-full transition-colors",
                isSpeaking
                  ? "text-primary bg-primary/10"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
              title={isSpeaking ? "Stop speaking" : "Read aloud"}
            >
              {isSpeaking ? (
                <VolumeX className="h-3 w-3" />
              ) : (
                <Volume2 className="h-3 w-3" />
              )}
            </button>
          )}
          <p className="text-xs text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </div>
      </div>
    </div>
  );
}

