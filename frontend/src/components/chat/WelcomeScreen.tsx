"use client";

import { Zap, TrendingUp, Search, Lightbulb } from "lucide-react";
import { Card } from "@/components/ui/card";

interface WelcomeScreenProps {
  onExampleClick: (message: string) => void;
}

const EXAMPLE_PROMPTS = [
  {
    icon: TrendingUp,
    title: "Market Analysis",
    prompt: "What are the key market trends for AI companies in 2024?",
  },
  {
    icon: Search,
    title: "Research Query",
    prompt: "Summarize the latest developments in large language models",
  },
  {
    icon: Lightbulb,
    title: "Industry Insights",
    prompt: "What factors are driving the growth of cloud computing?",
  },
];

export function WelcomeScreen({ onExampleClick }: WelcomeScreenProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-start px-4 pt-8 pb-8 overflow-y-auto">
      <div className="mx-auto max-w-2xl text-center mt-4">
        {/* Logo */}
        <div className="mb-6 flex justify-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary">
            <Zap className="h-8 w-8 text-primary-foreground" />
          </div>
        </div>

        {/* Title */}
        <h1 className="mb-2 text-3xl font-bold">Welcome to IntelliStream</h1>
        <p className="mb-8 text-muted-foreground">
          Real-Time Agentic RAG Intelligence Platform powered by a 6-agent
          LangGraph workflow. Ask questions about your documents and get
          intelligent, cited responses.
        </p>

        {/* Features */}
        <div className="mb-8 grid gap-4 sm:grid-cols-3">
          <FeatureCard
            icon={<Search className="h-5 w-5" />}
            title="Hybrid Search"
            description="Vector + keyword search for accurate retrieval"
          />
          <FeatureCard
            icon={<Zap className="h-5 w-5" />}
            title="6-Agent Workflow"
            description="Router, Research, Analysis, Synthesis, Reflection, Response"
          />
          <FeatureCard
            icon={<Lightbulb className="h-5 w-5" />}
            title="Smart Insights"
            description="Entity extraction, sentiment analysis, and more"
          />
        </div>

        {/* Example Prompts */}
        <div>
          <p className="mb-3 text-sm text-muted-foreground">
            Try one of these examples:
          </p>
          <div className="grid gap-3 sm:grid-cols-3">
            {EXAMPLE_PROMPTS.map((example, index) => (
              <button
                key={index}
                onClick={() => onExampleClick(example.prompt)}
                className="group flex flex-col items-start gap-2 rounded-lg border border-border bg-card p-4 text-left transition-colors hover:border-primary hover:bg-accent"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                  <example.icon className="h-4 w-4" />
                </div>
                <div>
                  <p className="font-medium">{example.title}</p>
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {example.prompt}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <Card className="p-4 text-center">
      <div className="mb-2 flex justify-center text-primary">{icon}</div>
      <h3 className="text-sm font-medium">{title}</h3>
      <p className="text-xs text-muted-foreground">{description}</p>
    </Card>
  );
}
