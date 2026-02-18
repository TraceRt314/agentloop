import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentLoop — Multi-Agent Orchestration",
  description: "Watch your AI agents work autonomously in a pixel-art office",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  );
}
