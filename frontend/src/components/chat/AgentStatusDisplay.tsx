"use client";

import { Check, Loader2, Circle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentStatus } from "@/types";

interface AgentStatusDisplayProps {
  status: AgentStatus;
}

const AGENT_INFO = {
  router: { label: "Router", description: "Classifying query" },
  research: { label: "Research", description: "Retrieving documents" },
  analysis: { label: "Analysis", description: "Extracting insights" },
  synthesizer: { label: "Synthesis", description: "Building response" },
  reflection: { label: "Reflect", description: "Self-critiquing response" },
  response: { label: "Response", description: "Formatting output" },
};

const AGENT_ORDER: (keyof typeof AGENT_INFO)[] = [
  "router",
  "research",
  "analysis",
  "synthesizer",
  "reflection",
  "response",
];

export function AgentStatusDisplay({ status }: AgentStatusDisplayProps) {
  return (
    <div className="flex items-center justify-center gap-1">
      {AGENT_ORDER.map((agent, index) => {
        const agentStatus = status[agent] || "pending";
        return (
          <div key={agent} className="flex items-center">
            <AgentBadge
              agent={agent}
              status={agentStatus as "pending" | "running" | "completed"}
            />
            {index < AGENT_ORDER.length - 1 && (
              <div
                className={cn(
                  "mx-1 h-px w-4 transition-colors",
                  agentStatus === "completed"
                    ? "bg-primary"
                    : "bg-muted-foreground/30"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

interface AgentBadgeProps {
  agent: keyof AgentStatus;
  status: "pending" | "running" | "completed";
}

function AgentBadge({ agent, status }: AgentBadgeProps) {
  const info = AGENT_INFO[agent];

  // Skip rendering if agent info is not found
  if (!info) {
    return null;
  }

  return (
    <div
      className={cn(
        "flex items-center gap-1.5 rounded-full px-2 py-1 text-xs transition-colors",
        status === "completed" && "bg-primary/10 text-primary",
        status === "running" && "bg-primary/20 text-primary",
        status === "pending" && "bg-muted text-muted-foreground"
      )}
      title={info.description}
    >
      <StatusIcon status={status} />
      <span className="hidden sm:inline">{info.label}</span>
    </div>
  );
}

function StatusIcon({ status }: { status: "pending" | "running" | "completed" }) {
  if (status === "completed") {
    return <Check className="h-3 w-3" />;
  }
  if (status === "running") {
    return <Loader2 className="h-3 w-3 animate-spin" />;
  }
  return <Circle className="h-3 w-3" />;
}
