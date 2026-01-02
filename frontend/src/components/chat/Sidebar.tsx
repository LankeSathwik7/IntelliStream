"use client";

import { useState, useEffect } from "react";
import { X, Plus, MessageSquare, Trash2, Pencil, Check, PanelLeftClose, PanelLeft, Zap, Settings, LogIn, LogOut, User, Download, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Conversation } from "@/hooks/useConversations";
import type { User as SupabaseUser } from "@supabase/supabase-js";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onToggle: () => void;
  onNewChat: () => void;
  conversations: Conversation[];
  activeId: string | null;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, newTitle: string) => void;
  user?: SupabaseUser | null;
  onSettingsClick?: () => void;
  onLoginClick?: () => void;
  onLogoutClick?: () => void;
  onExportPDF?: () => Promise<void>;
  hasMessages?: boolean;
}

export function Sidebar({
  isOpen,
  onClose,
  onToggle,
  onNewChat,
  conversations,
  activeId,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
  user,
  onSettingsClick,
  onLoginClick,
  onLogoutClick,
  onExportPDF,
  hasMessages = false,
}: SidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    if (!onExportPDF || isExporting) return;
    setIsExporting(true);
    try {
      await onExportPDF();
    } finally {
      setIsExporting(false);
    }
  };

  // Prevent hydration mismatch by waiting for client mount
  useEffect(() => {
    setMounted(true);
  }, []);

  const formatDate = (date: Date): string => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return "Today";
    if (days === 1) return "Yesterday";
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  // During SSR and initial hydration, render a stable structure
  const showOverlay = mounted && isOpen;

  return (
    <>
      {/* Overlay - mobile only (only show after mount to prevent hydration mismatch) */}
      {showOverlay && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 border-r border-border bg-card overflow-hidden",
          "lg:relative lg:z-auto",
          // Only apply transitions after mount to prevent hydration flash
          mounted && "transition-transform duration-300 ease-in-out lg:transition-[width,border] lg:duration-200",
          // Use mounted check to ensure consistent SSR/client rendering
          (mounted ? isOpen : false)
            ? "translate-x-0 w-72"
            : "-translate-x-full lg:translate-x-0 lg:w-0 lg:border-r-0"
        )}
      >
        <div className={cn(
          "flex h-full flex-col w-72 shrink-0",
          !(mounted ? isOpen : false) && "lg:invisible"
        )}>
          {/* Header - IntelliStream Branding */}
          <div className="flex h-14 items-center justify-between border-b border-border px-4">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary shrink-0">
                <Zap className="h-5 w-5 text-primary-foreground" />
              </div>
              <span className="font-semibold">IntelliStream</span>
            </div>
            <div className="flex items-center gap-1">
              {/* Desktop collapse button */}
              <Button
                variant="ghost"
                size="icon"
                onClick={onToggle}
                className="hidden lg:flex"
                title="Collapse sidebar"
              >
                <PanelLeftClose className="h-5 w-5" />
              </Button>
              {/* Mobile close button */}
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="lg:hidden"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
          </div>

          {/* New Chat Button */}
          <div className="p-4">
            <Button className="w-full justify-start gap-2" variant="outline" onClick={onNewChat}>
              <Plus className="h-4 w-4" />
              New Chat
            </Button>
          </div>

          {/* Conversation List */}
          <div className="flex-1 overflow-y-auto px-2">
            <div className="space-y-1">
              {!conversations || conversations.length === 0 ? (
                <p className="px-3 py-4 text-sm text-muted-foreground text-center">
                  No conversations yet
                </p>
              ) : (
                (conversations || []).map((conv) => (
                  <ConversationItem
                    key={conv.id}
                    id={conv.id}
                    title={conv.title}
                    date={formatDate(conv.updatedAt)}
                    isActive={conv.id === activeId}
                    isEditing={editingId === conv.id}
                    onClick={() => {
                      if (editingId !== conv.id) {
                        onSelectConversation(conv.id);
                        onClose();
                      }
                    }}
                    onDelete={(e) => {
                      e.stopPropagation();
                      onDeleteConversation(conv.id);
                    }}
                    onStartEdit={(e) => {
                      e.stopPropagation();
                      setEditingId(conv.id);
                    }}
                    onSaveEdit={(newTitle) => {
                      onRenameConversation(conv.id, newTitle);
                      setEditingId(null);
                    }}
                    onCancelEdit={() => setEditingId(null)}
                  />
                ))
              )}
            </div>
          </div>

          {/* Footer - User Profile & Settings */}
          <div className="border-t border-border p-3 space-y-2">
            {/* Export PDF Button */}
            {hasMessages && onExportPDF && (
              <Button
                variant="ghost"
                className="w-full justify-start gap-3 h-10"
                onClick={handleExport}
                disabled={isExporting}
              >
                {isExporting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                <span>{isExporting ? "Exporting..." : "Export to PDF"}</span>
              </Button>
            )}

            {/* Settings Button */}
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 h-10"
              onClick={onSettingsClick}
            >
              <Settings className="h-4 w-4" />
              <span>Settings</span>
            </Button>

            {/* User Profile */}
            {user ? (
              <div className="flex items-center gap-3 rounded-lg px-3 py-2 bg-accent/50">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
                  <User className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user.email}</p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 shrink-0"
                  onClick={onLogoutClick}
                  title="Sign out"
                >
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <Button
                variant="outline"
                className="w-full justify-start gap-3 h-10"
                onClick={onLoginClick}
              >
                <LogIn className="h-4 w-4" />
                <span>Sign In</span>
              </Button>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}

interface ConversationItemProps {
  id: string;
  title: string;
  date: string;
  isActive?: boolean;
  isEditing?: boolean;
  onClick: () => void;
  onDelete: (e: React.MouseEvent) => void;
  onStartEdit: (e: React.MouseEvent) => void;
  onSaveEdit: (newTitle: string) => void;
  onCancelEdit: () => void;
}

function ConversationItem({
  id,
  title,
  date,
  isActive,
  isEditing,
  onClick,
  onDelete,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
}: ConversationItemProps) {
  const [editValue, setEditValue] = useState(title);

  const handleSave = () => {
    if (editValue.trim()) {
      onSaveEdit(editValue.trim());
    } else {
      onCancelEdit();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSave();
    } else if (e.key === "Escape") {
      setEditValue(title);
      onCancelEdit();
    }
  };

  if (isEditing) {
    return (
      <div className="flex items-center gap-2 rounded-lg px-3 py-2 bg-accent">
        <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
        <input
          type="text"
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleSave}
          autoFocus
          className="flex-1 min-w-0 bg-transparent border-none outline-none text-sm font-medium"
        />
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 shrink-0"
          onClick={handleSave}
        >
          <Check className="h-3 w-3" />
        </Button>
      </div>
    );
  }

  return (
    <div
      onClick={onClick}
      className={cn(
        "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors hover:bg-accent cursor-pointer",
        isActive && "bg-accent"
      )}
    >
      <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
      <div className="flex-1 min-w-0">
        <p className="truncate font-medium">{title}</p>
        <p className="text-xs text-muted-foreground">{date}</p>
      </div>
      <div className="flex shrink-0 opacity-0 group-hover:opacity-100">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 hover:bg-muted"
          onClick={onStartEdit}
        >
          <Pencil className="h-3 w-3" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
          onClick={onDelete}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
