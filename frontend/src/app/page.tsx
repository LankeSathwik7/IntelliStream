"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { Sidebar } from "@/components/chat/Sidebar";
import { Header } from "@/components/chat/Header";
import { SettingsModal } from "@/components/SettingsModal";
import { AuthModal } from "@/components/AuthModal";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useChat } from "@/hooks/useChat";
import { useConversations } from "@/hooks/useConversations";
import { useAuth } from "@/hooks/useAuth";
import { exportToPDF, downloadBlob } from "@/lib/api";
import type { Message } from "@/types";

// Load streaming speed from localStorage
function getStreamingSpeed(): "slow" | "medium" | "fast" {
  if (typeof window === "undefined") return "medium";
  try {
    const stored = localStorage.getItem("intellistream_settings");
    if (stored) {
      const settings = JSON.parse(stored);
      return settings.streamingSpeed || "medium";
    }
  } catch {
    // Ignore errors
  }
  return "medium";
}

export default function Home() {
  // Mounted state to prevent hydration mismatch
  const [mounted, setMounted] = useState(false);
  // Initialize sidebar state - start with false to match Sidebar's SSR render
  // Sidebar uses (mounted ? isOpen : false) so it renders closed during SSR
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [streamingSpeed, setStreamingSpeed] = useState<"slow" | "medium" | "fast">("medium");

  // Load sidebar state and streaming speed from localStorage after mount
  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem("sidebarOpen");
    // Default to true (open) if no saved preference
    setSidebarOpen(saved === null ? true : saved === "true");
    // Load streaming speed
    setStreamingSpeed(getStreamingSpeed());

    // Listen for settings changes
    const handleStorageChange = () => {
      setStreamingSpeed(getStreamingSpeed());
    };
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, []);

  // Persist sidebar state (only after mounted)
  useEffect(() => {
    if (mounted) {
      localStorage.setItem("sidebarOpen", String(sidebarOpen));
    }
  }, [sidebarOpen, mounted]);

  const {
    user,
    session,
    isLoading: authLoading,
    error: authError,
    signInWithEmail,
    signUpWithEmail,
    signInWithOAuth,
    signOut,
    clearError,
  } = useAuth();

  const {
    conversations,
    activeConversation,
    activeId,
    isLoaded,
    createConversation,
    updateConversation,
    deleteConversation,
    selectConversation,
    renameConversation,
  } = useConversations({ userId: user?.id || null });

  // Track the current activeId for the callbacks
  const activeIdRef = useRef<string | null>(activeId);
  activeIdRef.current = activeId;

  const handleMessagesChange = useCallback(
    (messages: Message[]) => {
      // Only update if we have an active conversation
      const currentActiveId = activeIdRef.current;
      if (currentActiveId) {
        updateConversation(currentActiveId, { messages });
      }
    },
    [updateConversation]
  );

  const handleThreadIdChange = useCallback(
    (threadId: string | null) => {
      const currentActiveId = activeIdRef.current;
      if (currentActiveId) {
        updateConversation(currentActiveId, { threadId });
      }
    },
    [updateConversation]
  );

  const chat = useChat({
    conversationId: activeId,
    initialMessages: activeConversation?.messages || [],
    initialThreadId: activeConversation?.threadId || null,
    onMessagesChange: handleMessagesChange,
    onThreadIdChange: handleThreadIdChange,
    accessToken: session?.access_token || null,
    streamingSpeed,
  });

  // Wrap sendMessage to ensure we have an active conversation
  const wrappedChat = {
    ...chat,
    sendMessage: async (content: string) => {
      // If no active conversation, create one first
      if (!activeIdRef.current && isLoaded) {
        const newId = createConversation();
        // Update the ref immediately so callbacks use the new ID
        activeIdRef.current = newId;
        // Small delay to let React state update
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      return chat.sendMessage(content);
    },
  };

  const handleNewChat = () => {
    createConversation();
    setSidebarOpen(false);
  };

  const handleSelectConversation = (id: string) => {
    selectConversation(id);
  };

  const handleDeleteConversation = (id: string) => {
    deleteConversation(id);
  };

  const handleRenameConversation = (id: string, newTitle: string) => {
    renameConversation(id, newTitle);
  };

  const handleExportPDF = useCallback(async () => {
    if (chat.messages.length === 0) return;

    const exportMessages = chat.messages.map((msg) => ({
      role: msg.role,
      content: msg.content,
      sources: msg.sources,
    }));

    const title = activeConversation?.title || "IntelliStream Conversation";

    try {
      const blob = await exportToPDF({
        messages: exportMessages,
        title,
        include_sources: true,
      });

      // Determine file extension based on content type
      const isHtml = blob.type.includes("html");
      const ext = isHtml ? "html" : "pdf";
      downloadBlob(blob, `intellistream-report.${ext}`);
    } catch (error) {
      console.error("Export failed:", error);
    }
  }, [chat.messages, activeConversation?.title]);

  return (
    <ErrorBoundary>
      <div className="flex h-full w-full bg-background overflow-hidden">
        {/* Sidebar */}
        <Sidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onToggle={() => setSidebarOpen((prev) => !prev)}
          onNewChat={handleNewChat}
          conversations={conversations}
          activeId={activeId}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={handleDeleteConversation}
          onRenameConversation={handleRenameConversation}
          user={user}
          onSettingsClick={() => setSettingsOpen(true)}
          onLoginClick={() => setAuthModalOpen(true)}
          onLogoutClick={signOut}
          onExportPDF={handleExportPDF}
          hasMessages={chat.messages.length > 0}
        />

        {/* Main Content - no transition to prevent header animation */}
        <div className="flex flex-1 flex-col min-w-0 h-full overflow-hidden">
          {/* Header - minimal, just menu toggle and logo */}
          <Header
            onMenuClick={() => setSidebarOpen((prev) => !prev)}
            sidebarOpen={sidebarOpen}
          />

          {/* Chat Interface - key forces remount on conversation or user change */}
          <main className="flex-1 min-h-0 overflow-hidden">
            <ChatInterface key={`${user?.id || 'guest'}-${activeId || 'new'}`} chat={wrappedChat} />
          </main>
        </div>

        {/* Settings Modal */}
        <SettingsModal
          isOpen={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          user={user}
          accessToken={session?.access_token}
        />

        {/* Auth Modal */}
        <AuthModal
          isOpen={authModalOpen}
          onClose={() => setAuthModalOpen(false)}
          onSignIn={signInWithEmail}
          onSignUp={signUpWithEmail}
          onOAuthSignIn={signInWithOAuth}
          isLoading={authLoading}
          error={authError}
          onClearError={clearError}
        />
      </div>
    </ErrorBoundary>
  );
}
