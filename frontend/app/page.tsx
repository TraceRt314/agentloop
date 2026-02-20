"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { useAgentWebSocket } from "@/lib/useWebSocket";
import EventFeed from "@/components/EventFeed";
import StatusPanel from "@/components/StatusPanel";
import TasksPanel from "@/components/TasksPanel";
import SystemPanel from "@/components/SystemPanel";
import ChatPanel from "@/components/ChatPanel";
import { pluginTabs, PluginTab } from "@/lib/plugin-registry";
import { pluginComponents } from "@/lib/plugin-components";

const IsometricOffice = dynamic(() => import("@/components/IsometricOffice"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center rounded-xl border border-slate-800 bg-slate-950/50" style={{ width: 700, height: 620 }}>
      <div className="ui-label text-slate-600 animate-pulse">loading office...</div>
    </div>
  ),
});

interface ProjectInfo {
  id: string;
  name: string;
  slug: string;
}

interface TabDef {
  id: string;
  label: string;
  plugin?: string;
}

// Core tabs always present
const CORE_TABS: TabDef[] = [
  { id: "office", label: "office" },
  { id: "tasks", label: "tasks" },
  { id: "chat", label: "chat" },
  { id: "system", label: "system" },
];


export default function Home() {
  const { agents, events, connected } = useAgentWebSocket();
  const [activeTab, setActiveTab] = useState<string>("office");
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [serverTabs, setServerTabs] = useState<PluginTab[]>([]);

  // Fetch projects on mount
  useEffect(() => {
    fetch("/api/v1/projects/")
      .then((r) => r.json())
      .then((data: ProjectInfo[]) => {
        setProjects(data || []);
        if (data?.length > 0 && !selectedProjectId) {
          setSelectedProjectId(data[0].id);
        }
      })
      .catch(() => {});
  }, []);

  // Fetch plugin tabs from the backend
  useEffect(() => {
    fetch("/api/v1/plugins/tabs")
      .then((r) => r.json())
      .then((data: PluginTab[]) => setServerTabs(data || []))
      .catch(() => {});
  }, []);

  // Merge core tabs with plugin tabs (deduplicate by id, plugins override core)
  const allTabs = useMemo(() => {
    // Start with core tabs
    const merged = new Map<string, TabDef>();
    for (const t of CORE_TABS) merged.set(t.id, t);

    // Add plugin tabs (from static registry or server) that aren't core
    const extraTabs = serverTabs.length > 0 ? serverTabs : pluginTabs;
    for (const pt of extraTabs) {
      if (!merged.has(pt.id)) {
        merged.set(pt.id, { id: pt.id, label: pt.label, plugin: pt.plugin });
      }
    }
    return Array.from(merged.values());
  }, [serverTabs]);

  // Filter agents by selected project
  const filteredAgents = useMemo(
    () =>
      selectedProjectId
        ? agents.filter((a) => a.project_id === selectedProjectId)
        : agents,
    [agents, selectedProjectId],
  );

  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  // Find if the active tab is a plugin tab
  const activeTabDef = allTabs.find((t) => t.id === activeTab);
  const isPluginTab = activeTabDef?.plugin && !["office", "tasks", "chat", "system"].includes(activeTab);

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="shrink-0 flex items-center justify-between px-5 py-2.5 border-b border-slate-800/60 bg-[#0f1419]">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">&#x25b6;</span>
            <span className="ui-label text-sm tracking-widest text-slate-200">agentloop</span>
          </div>
          <span className="text-slate-700 text-xs">|</span>
          {/* Project selector */}
          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            className="bg-transparent border border-slate-800/50 rounded px-2 py-0.5 text-[10px] text-slate-400 outline-none focus:border-blue-500/40 transition cursor-pointer"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id} className="bg-slate-900">
                {p.name}
              </option>
            ))}
          </select>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-0.5 bg-slate-900/80 rounded-md p-0.5 border border-slate-800/50">
          {allTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-1.5 rounded transition-all ui-label ${
                activeTab === tab.id
                  ? "bg-blue-600/20 text-blue-400 shadow-sm shadow-blue-500/10"
                  : "text-slate-600 hover:text-slate-400"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`} />
            <span className="ui-label text-slate-500">{connected ? "live" : "offline"}</span>
          </div>
          <div className="ui-label text-slate-600">{filteredAgents.length} agents</div>
        </div>
      </header>

      {/* Main content — flex-1 + min-h-0 enables child scroll */}
      <main className="flex-1 min-h-0 flex overflow-hidden">
        {activeTab === "office" && (
          <>
            <aside className="w-52 shrink-0 border-r border-slate-800/40 p-3 bg-[#0f1419]/60 overflow-y-auto">
              <StatusPanel agents={filteredAgents} connected={connected} />
            </aside>

            <section className="flex-1 flex items-center justify-center p-4 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-950/10 via-transparent to-purple-950/10" />
              <div className="relative z-10">
                <IsometricOffice agents={filteredAgents} width={700} height={620} />
              </div>
            </section>

            <aside className="w-64 shrink-0 border-l border-slate-800/40 p-3 bg-[#0f1419]/60 overflow-hidden flex flex-col">
              <EventFeed events={events} />
            </aside>
          </>
        )}

        {activeTab === "tasks" && (
          <div className="flex-1 min-h-0 overflow-hidden">
            <TasksPanel />
          </div>
        )}

        {activeTab === "chat" && (
          <div className="flex-1 min-h-0 overflow-hidden">
            <ChatPanel />
          </div>
        )}

        {activeTab === "system" && (
          <div className="flex-1 min-h-0 overflow-y-auto">
            <SystemPanel />
          </div>
        )}

        {isPluginTab && pluginComponents[activeTab] && (() => {
          const PluginComponent = pluginComponents[activeTab];
          return (
            <div className="flex-1 min-h-0 overflow-y-auto">
              <PluginComponent />
            </div>
          );
        })()}
      </main>

      {/* Footer */}
      <footer className="shrink-0 flex items-center justify-between px-5 py-1.5 border-t border-slate-800/40 bg-[#0f1419]">
        <span className="ui-label text-slate-800" style={{ fontSize: 9 }}>agentloop v0.1.0</span>
        <div className="flex items-center gap-4">
          <a href="/docs" target="_blank" className="ui-label text-slate-700 hover:text-slate-500 transition" style={{ fontSize: 9 }}>api docs</a>
        </div>
      </footer>
    </div>
  );
}
