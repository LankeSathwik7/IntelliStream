"use client";

import { useState, useEffect, useCallback } from "react";
import { X, Sun, Moon, Monitor, Volume2, VolumeX, Bell, BellOff, Loader2, Cloud, CloudOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getSettings, saveSettings as saveSettingsAPI } from "@/lib/api";
import type { User } from "@supabase/supabase-js";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  user?: User | null;
  accessToken?: string | null;
}

type Theme = "light" | "dark" | "system";

interface Settings {
  theme: Theme;
  soundEnabled: boolean;
  notificationsEnabled: boolean;
  streamingSpeed: "slow" | "medium" | "fast";
}

const defaultSettings: Settings = {
  theme: "light",
  soundEnabled: true,
  notificationsEnabled: true,
  streamingSpeed: "medium",
};

function loadLocalSettings(): Settings {
  if (typeof window === "undefined") return defaultSettings;
  try {
    const stored = localStorage.getItem("intellistream_settings");
    if (stored) {
      return { ...defaultSettings, ...JSON.parse(stored) };
    }
  } catch {
    // Ignore errors
  }
  return defaultSettings;
}

function saveLocalSettings(settings: Settings): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem("intellistream_settings", JSON.stringify(settings));
  } catch {
    // Ignore errors
  }
}

export function SettingsModal({ isOpen, onClose, user, accessToken }: SettingsModalProps) {
  const [settings, setSettings] = useState<Settings>(defaultSettings);
  const [mounted, setMounted] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [syncStatus, setSyncStatus] = useState<"synced" | "local" | "error">("local");

  // Load settings on mount and when user changes
  useEffect(() => {
    const loadSettings = async () => {
      // Always start with local settings
      const localSettings = loadLocalSettings();
      setSettings(localSettings);
      setMounted(true);

      // If user is logged in, try to load from server
      if (user && accessToken) {
        try {
          const response = await getSettings(accessToken);
          if (response.success && response.settings) {
            const serverSettings = {
              theme: response.settings.theme as Theme,
              soundEnabled: response.settings.soundEnabled,
              notificationsEnabled: response.settings.notificationsEnabled,
              streamingSpeed: response.settings.streamingSpeed as Settings["streamingSpeed"],
            };
            setSettings(serverSettings);
            saveLocalSettings(serverSettings); // Update local cache
            setSyncStatus("synced");
          }
        } catch {
          setSyncStatus("error");
        }
      } else {
        setSyncStatus("local");
      }
    };

    loadSettings();
  }, [user, accessToken]);

  // Apply theme when settings change
  useEffect(() => {
    if (!mounted) return;

    const applyTheme = (theme: Theme) => {
      const root = document.documentElement;

      if (theme === "system") {
        const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        root.classList.toggle("dark", systemDark);
      } else {
        root.classList.toggle("dark", theme === "dark");
      }
    };

    applyTheme(settings.theme);
  }, [settings.theme, mounted]);

  // Debounced save to server
  const saveToServer = useCallback(async (newSettings: Settings) => {
    // Always save locally first
    saveLocalSettings(newSettings);

    // If logged in, sync to server
    if (user && accessToken) {
      setIsSaving(true);
      try {
        await saveSettingsAPI(newSettings, accessToken);
        setSyncStatus("synced");
      } catch {
        setSyncStatus("error");
      } finally {
        setIsSaving(false);
      }
    }
  }, [user, accessToken]);

  const updateSetting = useCallback(<K extends keyof Settings>(key: K, value: Settings[K]) => {
    setSettings((prev) => {
      const newSettings = { ...prev, [key]: value };
      saveToServer(newSettings);
      return newSettings;
    });
  }, [saveToServer]);

  if (!isOpen) return null;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-card p-6 shadow-lg">
        {/* Header with close button */}
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-semibold">Settings</h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Sync status below header */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-6">
          {isSaving ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>Saving...</span>
            </>
          ) : user ? (
            syncStatus === "synced" ? (
              <>
                <Cloud className="h-3 w-3 text-green-500" />
                <span className="text-green-600 dark:text-green-400">Synced to cloud</span>
              </>
            ) : syncStatus === "error" ? (
              <>
                <CloudOff className="h-3 w-3 text-red-500" />
                <span className="text-red-600 dark:text-red-400">Sync error</span>
              </>
            ) : null
          ) : (
            <span className="text-muted-foreground">Local only • Sign in to sync</span>
          )}
        </div>

        <div className="space-y-6">
          {/* Theme */}
          <div>
            <label className="mb-3 block text-sm font-medium">Theme</label>
            <div className="flex gap-2">
              {[
                { value: "light" as Theme, icon: Sun, label: "Light" },
                { value: "dark" as Theme, icon: Moon, label: "Dark" },
                { value: "system" as Theme, icon: Monitor, label: "System" },
              ].map(({ value, icon: Icon, label }) => (
                <button
                  key={value}
                  onClick={() => updateSetting("theme", value)}
                  className={cn(
                    "flex flex-1 flex-col items-center gap-2 rounded-lg border p-3 transition-colors",
                    settings.theme === value
                      ? "border-primary bg-primary/10"
                      : "border-border hover:bg-accent"
                  )}
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-xs">{label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Sound */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {settings.soundEnabled ? (
                <Volume2 className="h-5 w-5 text-muted-foreground" />
              ) : (
                <VolumeX className="h-5 w-5 text-muted-foreground" />
              )}
              <div>
                <p className="text-sm font-medium">Sound Effects</p>
                <p className="text-xs text-muted-foreground">
                  Play sounds for notifications
                </p>
              </div>
            </div>
            <button
              onClick={() => updateSetting("soundEnabled", !settings.soundEnabled)}
              className={cn(
                "relative h-6 w-11 rounded-full transition-colors",
                settings.soundEnabled ? "bg-primary" : "bg-muted"
              )}
            >
              <span
                className={cn(
                  "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform",
                  settings.soundEnabled ? "left-[22px]" : "left-0.5"
                )}
              />
            </button>
          </div>

          {/* Notifications */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {settings.notificationsEnabled ? (
                <Bell className="h-5 w-5 text-muted-foreground" />
              ) : (
                <BellOff className="h-5 w-5 text-muted-foreground" />
              )}
              <div>
                <p className="text-sm font-medium">Notifications</p>
                <p className="text-xs text-muted-foreground">
                  Show browser notifications
                </p>
              </div>
            </div>
            <button
              onClick={() => updateSetting("notificationsEnabled", !settings.notificationsEnabled)}
              className={cn(
                "relative h-6 w-11 rounded-full transition-colors",
                settings.notificationsEnabled ? "bg-primary" : "bg-muted"
              )}
            >
              <span
                className={cn(
                  "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform",
                  settings.notificationsEnabled ? "left-[22px]" : "left-0.5"
                )}
              />
            </button>
          </div>

          {/* Streaming Speed */}
          <div>
            <label className="mb-3 block text-sm font-medium">Response Streaming Speed</label>
            <div className="flex gap-2">
              {[
                { value: "slow" as const, label: "Slow" },
                { value: "medium" as const, label: "Medium" },
                { value: "fast" as const, label: "Fast" },
              ].map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => updateSetting("streamingSpeed", value)}
                  className={cn(
                    "flex-1 rounded-lg border px-4 py-2 text-sm transition-colors",
                    settings.streamingSpeed === value
                      ? "border-primary bg-primary/10"
                      : "border-border hover:bg-accent"
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-border">
          <p className="text-xs text-muted-foreground text-center">
            {user ? (
              <>Settings synced to your account</>
            ) : (
              <>Sign in to sync settings across devices</>
            )}
          </p>
        </div>
      </div>
    </>
  );
}
