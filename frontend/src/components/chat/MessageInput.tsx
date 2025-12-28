"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Plus, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface MessageInputProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  isUploading?: boolean;
  onFileUpload?: (file: File) => void;
  onImageUpload?: (file: File) => void;
}

export function MessageInput({ onSend, isLoading, isUploading, onFileUpload, onImageUpload }: MessageInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [input]);

  const canSend = input.trim() && !isLoading && !isUploading;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (canSend) {
      onSend(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    // Support multiple files
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'webp'];

      if (file.type.startsWith('image/') || imageExts.includes(ext)) {
        onImageUpload?.(file);
      } else {
        onFileUpload?.(file);
      }
    }
    // Reset input so same file can be selected again
    e.target.value = "";
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
      <div className="flex items-end gap-2">
        {/* Hidden file input - accepts PDFs and images, multiple */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf,.txt,.doc,.docx,.jpg,.jpeg,.png,.gif,.webp,image/*"
          onChange={handleFileSelect}
          className="hidden"
          multiple
        />

        {/* Upload Button */}
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={handleUploadClick}
          className="shrink-0"
          title="Upload PDF, Document, or Image"
          disabled={isLoading}
        >
          <Plus className="h-5 w-5" />
        </Button>

        {/* Input Area */}
        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isUploading ? "Wait for upload to complete..." : "Ask anything about your data..."}
            className={cn(
              "w-full resize-none rounded-lg border border-input bg-background px-4 py-3 pr-12 text-sm",
              "placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
              "disabled:cursor-not-allowed disabled:opacity-50"
            )}
            disabled={isLoading}
            rows={1}
          />

          {/* Send Button */}
          <Button
            type="submit"
            size="icon"
            className="absolute bottom-2 right-2 h-8 w-8"
            disabled={!canSend}
            title={isUploading ? "Wait for upload to complete" : "Send message"}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      <p className="mt-2 text-center text-xs text-muted-foreground">
        {isUploading ? "Uploading files..." : "Press Enter to send, Shift + Enter for new line"}
      </p>
    </form>
  );
}
