"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { useAgentWebSocket } from "@/lib/useWebSocket";
import EventFeed from "@/components/EventFeed";
import StatusPanel from "@/components/StatusPanel";
import TasksPanel from "@/components/TasksPanel";
import SystemPanel from "@/components/SystemPanel";

const IsometricOffice = dynamic(() => import("@/components/IsometricOffice"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center rounded-xl border-2 border-slate-700 bg-slate-950" style={{ width: 700, height: 620 }}>
      <div className="ui-label text-slate-600 text-xs animate-pulse">Loading office...</div>
    </div>
  ),
});

type Tab = "office" | "tasks" | "system";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "office", label: "Office", icon: "🏢" },
  { id: "tasks", label: "Tasks", icon: "📋" },
  { id: "system", label: "System", icon: "🖥️" },
];

export default function Home() {
  const { agents, events, connected } = useAgentWebSocket();
  const [activeTab, setActiveTab] = useState<Tab>("office");

  return (
    <div className="min-h-screen flex flex-col bg-[#0d1117]">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-slate-800/50 bg-[#161b22]/80 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="text-2xl">🔄</div>
            <div className="absolute -bottom-1 -right-1 w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          </div>
          <div>
            <h1 className="ui-label text-sm tracking-wider text-white">AGENTLOOP</h1>
            <p className="text-[10px] text-slate-500 mt-0.5">Multi-Agent Orchestration Platform</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 bg-slate-800/50 rounded-lg p-1 border border-slate-700/30">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-md transition-all ui-label ${
                activeTab === tab.id
                  ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                  : "text-slate-500 hover:text-slate-300 border border-transparent"
              }`}
              style={{ fontSize: 9 }}
            >
              <span className="text-sm">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-500 animate-pulse" : "bg-red-500"}`} />
            <span className="ui-label" style={{ fontSize: 8 }}>{connected ? "LIVE" : "OFFLINE"}</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700/50">
            <span className="text-xs">🤖</span>
            <span className="ui-label text-slate-400" style={{ fontSize: 8 }}>{agents.length} AGENTS</span>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex overflow-hidden">
        {activeTab === "office" && (
          <>
            {/* Left panel */}
            <aside className="w-56 border-r border-slate-800/50 p-4 bg-[#161b22]/50 overflow-y-auto">
              <StatusPanel agents={agents} connected={connected} />
            </aside>

            {/* Center - Isometric Office */}
            <section className="flex-1 flex items-center justify-center p-4 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-950/20 via-transparent to-purple-950/20" />
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-3xl" />
              <div className="relative z-10">
                <IsometricOffice agents={agents} width={700} height={620} />
              </div>
            </section>

            {/* Right panel */}
            <aside className="w-72 border-l border-slate-800/50 p-4 bg-[#161b22]/50 overflow-hidden flex flex-col">
              <EventFeed events={events} />
            </aside>
          </>
        )}

        {activeTab === "tasks" && (
          <div className="flex-1 bg-[#0d1117]">
            <TasksPanel />
          </div>
        )}

        {activeTab === "system" && (
          <div className="flex-1 bg-[#0d1117] overflow-y-auto">
            <SystemPanel />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="flex items-center justify-between px-6 py-2 border-t border-slate-800/50 bg-[#161b22]/80">
        <div className="ui-label text-slate-700" style={{ fontSize: 7 }}>
          AgentLoop v0.1.0 — Open Source Multi-Agent Platform
        </div>
        <div className="flex items-center gap-4">
          <a href="http://localhost:8080/docs" target="_blank" className="text-[10px] text-slate-600 hover:text-slate-400 transition">API Docs</a>
          <a href="http://localhost:3001" target="_blank" className="text-[10px] text-slate-600 hover:text-slate-400 transition">Mission Control ↗</a>
        </div>
      </footer>
    </div>
  );
}
