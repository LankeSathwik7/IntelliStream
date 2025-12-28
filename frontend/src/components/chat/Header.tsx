"use client";

import { Menu, Zap, PanelLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface HeaderProps {
  onMenuClick: () => void;
  sidebarOpen?: boolean;
}

export function Header({
  onMenuClick,
  sidebarOpen = false,
}: HeaderProps) {
  return (
    <header className="flex h-12 shrink-0 items-center border-b border-border bg-background px-4">
      <div className="flex items-center gap-3">
        {/* Mobile menu button - always rendered, visibility controlled by CSS */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onMenuClick}
          className="lg:hidden"
          title="Open menu"
        >
          <Menu className="h-5 w-5" />
        </Button>
        {/* Desktop expand button - always rendered, visibility controlled by CSS and state */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onMenuClick}
          className={cn(
            "hidden",
            !sidebarOpen && "lg:flex"
          )}
          title="Expand sidebar"
        >
          <PanelLeft className="h-5 w-5" />
        </Button>

        {/* Logo only - shown when sidebar is collapsed on desktop or always on mobile */}
        <div className={cn(
          "flex items-center gap-2",
          sidebarOpen && "lg:hidden"
        )}>
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary shrink-0">
            <Zap className="h-4 w-4 text-primary-foreground" />
          </div>
        </div>
      </div>
    </header>
  );
}
