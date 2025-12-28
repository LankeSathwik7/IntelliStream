import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "IntelliStream - Real-Time Agentic RAG Intelligence",
  description:
    "A Real-Time Agentic RAG Intelligence Platform powered by 6-agent LangGraph workflow",
  keywords: ["RAG", "AI", "LangGraph", "Intelligence", "Agents"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        {/* Inline script to set theme before page renders to avoid flash */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var stored = localStorage.getItem('intellistream_settings');
                  if (stored) {
                    var settings = JSON.parse(stored);
                    var theme = settings.theme;
                    if (theme === 'dark') {
                      document.documentElement.classList.add('dark');
                    } else if (theme === 'system') {
                      if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
                        document.documentElement.classList.add('dark');
                      }
                    }
                    // else light theme - no class needed
                  }
                  // If no settings stored, default is light (no dark class)
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className={`${inter.className} h-full overflow-hidden`}>{children}</body>
    </html>
  );
}
