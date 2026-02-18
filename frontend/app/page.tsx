"use client";

import { useAgentWebSocket } from "@/lib/useWebSocket";
import Office from "@/components/Office";
import EventFeed from "@/components/EventFeed";
import StatusPanel from "@/components/StatusPanel";

export default function Home() {
  const { agents, events, connected } = useAgentWebSocket();

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-slate-800 bg-slate-900/80 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="text-2xl">🔄</div>
          <div>
            <h1 className="pixel-font text-sm tracking-wider text-white">AGENTLOOP</h1>
            <p className="text-xs text-slate-500">Multi-Agent Orchestration System</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-500 animate-pulse" : "bg-red-500"}`} />
            {connected ? "Live" : "Reconnecting..."}
          </div>
          <div className="pixel-font text-xs text-slate-600">
            {agents.length} agent{agents.length !== 1 ? "s" : ""}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex gap-0">
        {/* Left panel - Agent status */}
        <aside className="w-64 border-r border-slate-800 p-4 bg-slate-900/50 overflow-y-auto">
          <StatusPanel agents={agents} connected={connected} />
        </aside>

        {/* Center - Office view */}
        <section className="flex-1 flex items-center justify-center p-6 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
          <div className="relative">
            <Office agents={agents} width={560} height={500} />
            
            {/* Glow effect under office */}
            <div
              className="absolute -bottom-4 left-1/2 -translate-x-1/2 rounded-full blur-xl opacity-20"
              style={{
                width: 400,
                height: 20,
                background: "linear-gradient(90deg, #4ade80, #60a5fa, #a78bfa)",
              }}
            />
          </div>
        </section>

        {/* Right panel - Event feed */}
        <aside className="w-80 border-l border-slate-800 p-4 bg-slate-900/50 overflow-hidden flex flex-col">
          <EventFeed events={events} />
        </aside>
      </main>

      {/* Footer */}
      <footer className="flex items-center justify-between px-6 py-2 border-t border-slate-800 bg-slate-900/80">
        <div className="pixel-font text-slate-600" style={{ fontSize: 7 }}>
          AgentLoop v0.1.0 — Open Source Multi-Agent System
        </div>
        <div className="flex items-center gap-3">
          <a href="/docs" className="text-xs text-slate-500 hover:text-slate-300 transition">API Docs</a>
          <a href="http://localhost:3001" target="_blank" className="text-xs text-slate-500 hover:text-slate-300 transition">Mission Control ↗</a>
        </div>
      </footer>
    </div>
  );
}
