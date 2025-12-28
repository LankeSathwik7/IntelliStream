"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import type { Message } from "@/types";

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  threadId: string | null;
  createdAt: Date;
  updatedAt: Date;
}

const STORAGE_KEY_PREFIX = "intellistream_conversations";

function getStorageKey(userId: string | null): string {
  return userId ? `${STORAGE_KEY_PREFIX}_${userId}` : `${STORAGE_KEY_PREFIX}_guest`;
}

function generateId(): string {
  return `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

function generateTitle(messages: Message[]): string {
  const firstUserMessage = messages.find((m) => m.role === "user");
  if (firstUserMessage) {
    const content = firstUserMessage.content.trim();
    // Remove context hints from title
    const cleanContent = content.replace(/^\[Context:[\s\S]*?\]\n\n/, "").trim();
    return cleanContent.length > 40 ? cleanContent.slice(0, 40) + "..." : cleanContent;
  }
  return "New Conversation";
}

function loadFromStorage(userId: string | null): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    const key = getStorageKey(userId);
    const stored = localStorage.getItem(key);
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.map((conv: Conversation) => ({
        ...conv,
        createdAt: new Date(conv.createdAt),
        updatedAt: new Date(conv.updatedAt),
        messages: conv.messages.map((m: Message) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        })),
      }));
    }
  } catch (e) {
    console.error("Failed to load conversations:", e);
  }
  return [];
}

function saveToStorage(userId: string | null, conversations: Conversation[]): void {
  if (typeof window === "undefined") return;
  try {
    const key = getStorageKey(userId);
    localStorage.setItem(key, JSON.stringify(conversations));
  } catch (e) {
    console.error("Failed to save conversations:", e);
  }
}

interface UseConversationsOptions {
  userId?: string | null;
}

export function useConversations(options: UseConversationsOptions = {}) {
  const { userId = null } = options;

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  // Track current userId to detect changes
  const currentUserIdRef = useRef<string | null>(userId);

  // Load from localStorage on mount and when userId changes
  useEffect(() => {
    // Detect if userId changed
    const userChanged = currentUserIdRef.current !== userId;
    currentUserIdRef.current = userId;

    const loaded = loadFromStorage(userId);
    setConversations(loaded);

    // Always reset activeId when user changes or there are no conversations
    if (loaded.length > 0) {
      setActiveId(loaded[0].id);
    } else {
      setActiveId(null);
    }
    setIsLoaded(true);
  }, [userId]);

  // Save to localStorage when conversations change
  useEffect(() => {
    if (isLoaded) {
      saveToStorage(userId, conversations);
    }
  }, [userId, conversations, isLoaded]);

  const activeConversation = conversations.find((c) => c.id === activeId) || null;

  const createConversation = useCallback((): string => {
    const newConv: Conversation = {
      id: generateId(),
      title: "New Conversation",
      messages: [],
      threadId: null,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    setConversations((prev) => [newConv, ...prev]);
    setActiveId(newConv.id);
    return newConv.id;
  }, []);

  const updateConversation = useCallback(
    (id: string, updates: Partial<Pick<Conversation, "messages" | "threadId">>) => {
      setConversations((prev) =>
        prev.map((conv) => {
          if (conv.id !== id) return conv;
          const updated = {
            ...conv,
            ...updates,
            updatedAt: new Date(),
          };
          // Auto-update title based on first user message
          if (updates.messages && updates.messages.length > 0) {
            updated.title = generateTitle(updates.messages);
          }
          return updated;
        })
      );
    },
    []
  );

  const deleteConversation = useCallback(
    (id: string) => {
      // Use functional updates to avoid stale closure issues
      setConversations((prev) => {
        const filtered = prev.filter((c) => c.id !== id);
        // Save to localStorage immediately within the same update
        saveToStorage(userId, filtered);
        return filtered;
      });

      // Update activeId using functional update
      setActiveId((currentActiveId) => {
        if (currentActiveId === id) {
          // Will be corrected by the effect below if there are remaining conversations
          return null;
        }
        return currentActiveId;
      });
    },
    [userId]
  );

  // Auto-select first conversation when activeId is null but we have conversations
  useEffect(() => {
    if (isLoaded && activeId === null && conversations.length > 0) {
      setActiveId(conversations[0].id);
    }
  }, [isLoaded, activeId, conversations]);

  const selectConversation = useCallback((id: string) => {
    setActiveId(id);
  }, []);

  const renameConversation = useCallback((id: string, newTitle: string) => {
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === id
          ? { ...conv, title: newTitle, updatedAt: new Date() }
          : conv
      )
    );
  }, []);

  return {
    conversations,
    activeConversation,
    activeId,
    isLoaded,
    createConversation,
    updateConversation,
    deleteConversation,
    selectConversation,
    renameConversation,
  };
}
