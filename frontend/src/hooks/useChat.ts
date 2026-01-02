"use client";

import { useState, useCallback, useRef } from "react";
import { streamChatMessage } from "@/lib/api";
import { playSuccessSound, playErrorSound } from "@/lib/sounds";
import { showResponseNotification, showErrorNotification } from "@/lib/notifications";
import type { Message, AgentStatus, Attachment } from "@/types";

// Generate unique ID with counter to prevent collisions
let idCounter = 0;
const generateId = (prefix: string) => {
  idCounter++;
  return `${prefix}-${Date.now()}-${idCounter}-${Math.random().toString(36).substr(2, 9)}`;
};

const initialAgentStatus: AgentStatus = {
  router: "pending",
  research: "pending",
  analysis: "pending",
  synthesizer: "pending",
  reflection: "pending",
  response: "pending",
};

interface UseChatOptions {
  conversationId?: string | null;
  initialMessages?: Message[];
  initialThreadId?: string | null;
  onMessagesChange?: (messages: Message[]) => void;
  onThreadIdChange?: (threadId: string | null) => void;
  accessToken?: string | null;
  streamingSpeed?: "slow" | "medium" | "fast";
}

export function useChat(options: UseChatOptions = {}) {
  const {
    conversationId = null,
    initialMessages = [],
    initialThreadId = null,
    onMessagesChange,
    onThreadIdChange,
    accessToken = null,
    streamingSpeed = "medium",
  } = options;

  // Track the last conversation ID to detect switches
  const lastConversationIdRef = useRef<string | null>(conversationId);
  const isInitializedRef = useRef(false);

  // Initialize or reset state based on conversation switch
  const getInitialMessages = () => {
    if (conversationId !== lastConversationIdRef.current) {
      lastConversationIdRef.current = conversationId;
      return initialMessages;
    }
    return isInitializedRef.current ? undefined : initialMessages;
  };

  const getInitialThreadId = () => {
    if (conversationId !== lastConversationIdRef.current) {
      return initialThreadId;
    }
    return isInitializedRef.current ? undefined : initialThreadId;
  };

  const [messages, setMessagesInternal] = useState<Message[]>(() => initialMessages);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [threadId, setThreadIdInternal] = useState<string | null>(initialThreadId);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>(initialAgentStatus);

  // Handle conversation switches
  if (conversationId !== lastConversationIdRef.current) {
    lastConversationIdRef.current = conversationId;
    setMessagesInternal(initialMessages);
    setThreadIdInternal(initialThreadId);
    setAgentStatus(initialAgentStatus);
    setError(null);
    setIsLoading(false);
  }

  isInitializedRef.current = true;

  // Wrapper to also notify parent
  const setMessages = useCallback((updater: Message[] | ((prev: Message[]) => Message[])) => {
    setMessagesInternal((prev) => {
      const newMessages = typeof updater === 'function' ? updater(prev) : updater;
      // Notify parent asynchronously to avoid render cycle issues
      setTimeout(() => onMessagesChange?.(newMessages), 0);
      return newMessages;
    });
  }, [onMessagesChange]);

  const setThreadId = useCallback((newThreadId: string | null) => {
    setThreadIdInternal(newThreadId);
    setTimeout(() => onThreadIdChange?.(newThreadId), 0);
  }, [onThreadIdChange]);

  const resetAgentStatus = useCallback(() => {
    setAgentStatus(initialAgentStatus);
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      setIsLoading(true);
      setError(null);
      resetAgentStatus();

      // Add user message
      const userMessage: Message = {
        id: generateId("user"),
        role: "user",
        content,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);

      // Add placeholder assistant message
      const assistantId = generateId("assistant");
      const assistantMessage: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      try {
        let fullContent = "";
        let sources: Message["sources"] = [];

        // Build conversation history (limit to last 20 messages to control token usage)
        const MAX_HISTORY = 20;
        const history = messages
          .filter((m) => m.role === "user" || m.role === "assistant")
          .slice(-MAX_HISTORY)
          .map((m) => ({
            role: m.role,
            content: m.content.slice(0, 2000),  // Truncate very long messages
          }));

        for await (const event of streamChatMessage({
          message: content,
          thread_id: threadId || undefined,
          history: history.length > 0 ? history : undefined,
          streaming_speed: streamingSpeed,
        }, accessToken || undefined)) {
          if (event.type === "agent_status" && event.data?.agent) {
            const agent = event.data.agent as keyof AgentStatus;
            const status = event.data.status === "started" ? "running" : "completed";
            setAgentStatus((prev) => ({ ...prev, [agent]: status }));
          } else if (event.type === "token" && event.data?.content) {
            // Update message progressively with streaming content
            const streamedContent = event.data.content;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, content: streamedContent, isStreaming: true }
                  : msg
              )
            );
          } else if (event.type === "response" && event.data?.content) {
            fullContent = event.data.content;
            sources = event.data.sources || [];
          } else if (event.type === "done" && event.data?.thread_id) {
            setThreadId(event.data.thread_id);
          } else if (event.type === "error") {
            throw new Error(event.data?.message || "Unknown error");
          }
        }

        // Update assistant message with final content and update user message version
        setMessages((prev) => {
          const result = prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content: fullContent, sources, isStreaming: false }
              : msg
          );

          // Find the user message before this assistant message and update its version
          const assistantIndex = result.findIndex((m) => m.id === assistantId);
          if (assistantIndex > 0) {
            const userMsg = result[assistantIndex - 1];
            if (userMsg.role === "user" && userMsg.versions && userMsg.versions.length > 0) {
              const updatedVersions = [...userMsg.versions];
              const lastVersionIndex = updatedVersions.length - 1;
              updatedVersions[lastVersionIndex] = {
                ...updatedVersions[lastVersionIndex],
                response: {
                  id: assistantId,
                  content: fullContent,
                  sources,
                  timestamp: new Date(),
                },
              };
              result[assistantIndex - 1] = { ...userMsg, versions: updatedVersions };
            }
          }

          return result;
        });

        // Play success sound and show notification when response completes
        playSuccessSound();
        showResponseNotification();
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "An error occurred";
        setError(errorMessage);

        // Play error sound and show notification
        playErrorSound();
        showErrorNotification(errorMessage);

        // Update assistant message with error
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  content: `Error: ${errorMessage}`,
                  isStreaming: false,
                }
              : msg
          )
        );
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, threadId, resetAgentStatus, messages, accessToken, streamingSpeed]
  );

  const sendMessageWithAttachments = useCallback(
    async (content: string, attachments: Attachment[]) => {
      if ((!content.trim() && attachments.length === 0) || isLoading) return;

      setIsLoading(true);
      setError(null);
      resetAgentStatus();

      // Add user message with attachments
      const userMessage: Message = {
        id: generateId("user"),
        role: "user",
        content,
        attachments,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);

      // Add placeholder assistant message
      const assistantId = generateId("assistant");
      const assistantMessage: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      try {
        let fullContent = "";
        let sources: Message["sources"] = [];

        // Build conversation history (limit to last 20 messages to control token usage)
        const MAX_HISTORY = 20;
        const history = messages
          .filter((m) => m.role === "user" || m.role === "assistant")
          .slice(-MAX_HISTORY)
          .map((m) => ({
            role: m.role,
            content: m.content.slice(0, 2000),  // Truncate very long messages
          }));

        for await (const event of streamChatMessage({
          message: content,
          thread_id: threadId || undefined,
          history: history.length > 0 ? history : undefined,
          streaming_speed: streamingSpeed,
        }, accessToken || undefined)) {
          if (event.type === "agent_status" && event.data?.agent) {
            const agent = event.data.agent as keyof AgentStatus;
            const status = event.data.status === "started" ? "running" : "completed";
            setAgentStatus((prev) => ({ ...prev, [agent]: status }));
          } else if (event.type === "token" && event.data?.content) {
            const streamedContent = event.data.content;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, content: streamedContent, isStreaming: true }
                  : msg
              )
            );
          } else if (event.type === "response" && event.data?.content) {
            fullContent = event.data.content;
            sources = event.data.sources || [];
          } else if (event.type === "done" && event.data?.thread_id) {
            setThreadId(event.data.thread_id);
          } else if (event.type === "error") {
            throw new Error(event.data?.message || "Unknown error");
          }
        }

        // Update assistant message with final content and update user message version
        setMessages((prev) => {
          const result = prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content: fullContent, sources, isStreaming: false }
              : msg
          );

          // Find the user message before this assistant message and update its version
          const assistantIndex = result.findIndex((m) => m.id === assistantId);
          if (assistantIndex > 0) {
            const userMsg = result[assistantIndex - 1];
            if (userMsg.role === "user" && userMsg.versions && userMsg.versions.length > 0) {
              const updatedVersions = [...userMsg.versions];
              const lastVersionIndex = updatedVersions.length - 1;
              updatedVersions[lastVersionIndex] = {
                ...updatedVersions[lastVersionIndex],
                response: {
                  id: assistantId,
                  content: fullContent,
                  sources,
                  timestamp: new Date(),
                },
              };
              result[assistantIndex - 1] = { ...userMsg, versions: updatedVersions };
            }
          }

          return result;
        });

        // Play success sound and show notification when response completes
        playSuccessSound();
        showResponseNotification();
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "An error occurred";
        setError(errorMessage);

        // Play error sound and show notification
        playErrorSound();
        showErrorNotification(errorMessage);

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content: `Error: ${errorMessage}`, isStreaming: false }
              : msg
          )
        );
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, threadId, resetAgentStatus, setMessages, messages, accessToken, streamingSpeed]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setThreadId(null);
    resetAgentStatus();
  }, [resetAgentStatus]);

  const editMessage = useCallback(
    async (messageId: string, newContent: string, resend: boolean = false) => {
      if (!newContent.trim()) return;

      // Find the message index
      const messageIndex = messages.findIndex((m) => m.id === messageId);
      if (messageIndex === -1) return;

      const message = messages[messageIndex];
      if (message.role !== "user") return; // Only edit user messages

      if (resend) {
        // Preserve attachments from the original message
        const attachments = message.attachments || [];

        // Find the assistant message that follows this user message
        const assistantMessage = messages[messageIndex + 1];
        const hasAssistantResponse = assistantMessage && assistantMessage.role === "assistant";

        // Store the current version before creating a new one
        const currentVersion = {
          id: message.id,
          content: message.content,
          timestamp: message.timestamp,
          response: hasAssistantResponse ? {
            id: assistantMessage.id,
            content: assistantMessage.content,
            sources: assistantMessage.sources,
            timestamp: assistantMessage.timestamp,
          } : undefined,
        };

        // Build versions array
        const existingVersions = message.versions || [];
        const allVersions = existingVersions.length === 0
          ? [currentVersion]  // First edit, save original as version 0
          : existingVersions;

        // Create new version for the edited message
        const newVersionId = generateId("version");
        const newVersion = {
          id: newVersionId,
          content: newContent,
          timestamp: new Date(),
          response: undefined, // Will be filled after response
        };

        // Update messages: keep messages up to this one, update the user message with versions
        setMessages((prev) => {
          const beforeEdit = prev.slice(0, messageIndex);
          const updatedUserMessage: Message = {
            ...message,
            content: newContent,
            timestamp: new Date(),
            versions: [...allVersions, newVersion],
            currentVersionIndex: allVersions.length, // Point to the new version
          };
          return [...beforeEdit, updatedUserMessage];
        });

        // Small delay to let state update
        await new Promise((resolve) => setTimeout(resolve, 10));

        // Send the new message
        if (attachments.length > 0) {
          await sendMessageWithAttachments(newContent, attachments);
        } else {
          await sendMessage(newContent);
        }

        // After sending, link the assistant response to this version
        // This happens automatically in sendMessage/sendMessageWithAttachments
      } else {
        // Just update the message content without resending
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === messageId
              ? { ...msg, content: newContent }
              : msg
          )
        );
      }
    },
    [messages, sendMessage, sendMessageWithAttachments, setMessages]
  );

  // Navigate between message versions
  const navigateVersion = useCallback(
    (messageId: string, direction: "prev" | "next") => {
      const messageIndex = messages.findIndex((m) => m.id === messageId);
      if (messageIndex === -1) return;

      const message = messages[messageIndex];
      if (!message.versions || message.versions.length <= 1) return;

      const currentIndex = message.currentVersionIndex ?? message.versions.length - 1;
      let newIndex: number;

      if (direction === "prev") {
        newIndex = Math.max(0, currentIndex - 1);
      } else {
        newIndex = Math.min(message.versions.length - 1, currentIndex + 1);
      }

      if (newIndex === currentIndex) return;

      const targetVersion = message.versions[newIndex];

      // Update the message and its assistant response
      setMessages((prev) => {
        const result: Message[] = [];
        let skipNext = false;

        for (let i = 0; i < prev.length; i++) {
          if (skipNext) {
            skipNext = false;
            continue;
          }

          const msg = prev[i];
          if (msg.id === messageId) {
            // Update user message
            result.push({
              ...msg,
              content: targetVersion.content,
              timestamp: targetVersion.timestamp,
              currentVersionIndex: newIndex,
            });

            // Check if next is assistant message and replace with version's response
            const nextMsg = prev[i + 1];
            if (nextMsg && nextMsg.role === "assistant") {
              skipNext = true;
              if (targetVersion.response) {
                result.push({
                  ...nextMsg,
                  id: targetVersion.response.id,
                  content: targetVersion.response.content,
                  sources: targetVersion.response.sources,
                  timestamp: targetVersion.response.timestamp,
                });
              }
              // If no response in version, don't add assistant message
            }
          } else {
            result.push(msg);
          }
        }

        return result;
      });
    },
    [messages, setMessages]
  );

  return {
    messages,
    isLoading,
    error,
    threadId,
    agentStatus,
    sendMessage,
    sendMessageWithAttachments,
    clearMessages,
    editMessage,
    navigateVersion,
  };
}
