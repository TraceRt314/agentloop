"use client";

import { useEffect, useState } from "react";

interface ServiceStatus {
  url: string;
  status: string;
}

interface DashboardOverview {
  agents: { name: string; role: string; current_action: string }[];
  projects: { name: string; slug: string }[];
  missions: { active: number; completed: number };
  proposals: { pending: number };
  steps: { running: number };
}

export default function SystemPanel() {
  const [services, setServices] = useState<Record<string, ServiceStatus>>({});
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [sysRes, overRes] = await Promise.all([
          fetch("/api/v1/dashboard/system"),
          fetch("/api/v1/dashboard/overview"),
        ]);
        if (sysRes.ok) {
          const d = await sysRes.json();
          setServices(d.services || {});
        }
        if (overRes.ok) {
          setOverview(await overRes.json());
        }
      } catch { /* ignore */ }
      setLoading(false);
    };
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  if (loading) {
    return <div className="p-6 text-center text-slate-600 ui-label text-xs animate-pulse">Checking systems...</div>;
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Services */}
      <div>
        <h3 className="ui-label text-xs text-slate-400 mb-4 flex items-center gap-2">
          <span>🖥️</span> SYSTEM SERVICES
        </h3>
        <div className="grid grid-cols-3 gap-3">
          {Object.entries(services).map(([name, svc]) => {
            const isHealthy = svc.status === "healthy";
            return (
              <div
                key={name}
                className={`p-4 rounded-xl border transition-all ${
                  isHealthy
                    ? "bg-green-500/5 border-green-500/20"
                    : "bg-red-500/5 border-red-500/20"
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className={`w-2.5 h-2.5 rounded-full ${isHealthy ? "bg-green-500 animate-pulse" : "bg-red-500"}`} />
                  <span className="text-sm text-slate-300 font-medium">
                    {name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </span>
                </div>
                <div className="text-xs text-slate-500 truncate">{svc.url}</div>
                <div className={`ui-label mt-2 ${isHealthy ? "text-green-400" : "text-red-400"}`} style={{ fontSize: 8 }}>
                  {svc.status.toUpperCase()}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Overview stats */}
      {overview && (
        <>
          <div>
            <h3 className="ui-label text-xs text-slate-400 mb-4 flex items-center gap-2">
              <span>📊</span> PLATFORM STATS
            </h3>
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: "Agents", value: overview.agents.length, icon: "🤖", color: "#60a5fa" },
                { label: "Projects", value: overview.projects.length, icon: "📁", color: "#4ade80" },
                { label: "Active Missions", value: overview.missions.active, icon: "🎯", color: "#fbbf24" },
                { label: "Pending Proposals", value: overview.proposals.pending, icon: "📝", color: "#a78bfa" },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="p-4 rounded-xl border border-slate-700/30 bg-slate-800/30"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">{stat.icon}</span>
                    <span className="ui-label text-2xl" style={{ color: stat.color }}>{stat.value}</span>
                  </div>
                  <div className="text-xs text-slate-500">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Projects */}
          <div>
            <h3 className="ui-label text-xs text-slate-400 mb-4 flex items-center gap-2">
              <span>📁</span> REGISTERED PROJECTS
            </h3>
            <div className="grid grid-cols-3 gap-3">
              {overview.projects.map((p) => (
                <div key={p.slug} className="p-3 rounded-lg border border-slate-700/30 bg-slate-800/20">
                  <div className="text-sm text-slate-300">{p.name}</div>
                  <div className="ui-label text-slate-600 mt-1" style={{ fontSize: 8 }}>{p.slug}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Agent activity */}
          <div>
            <h3 className="ui-label text-xs text-slate-400 mb-4 flex items-center gap-2">
              <span>🤖</span> AGENT ACTIVITY
            </h3>
            <div className="grid grid-cols-4 gap-3">
              {overview.agents.map((a) => {
                const actionColors: Record<string, string> = {
                  idle: "#64748b", working: "#4ade80", walking: "#60a5fa",
                  thinking: "#fbbf24", talking: "#a78bfa", reviewing: "#f87171",
                };
                return (
                  <div key={a.name} className="p-3 rounded-lg border border-slate-700/30 bg-slate-800/20 text-center">
                    <div className="text-sm text-slate-300 font-medium">{a.name}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{a.role.replace("_", " ")}</div>
                    <div
                      className="ui-label mt-2 px-2 py-1 rounded-full inline-block"
                      style={{
                        fontSize: 8,
                        color: actionColors[a.current_action] ?? "#8892b0",
                        background: `${actionColors[a.current_action] ?? "#8892b0"}15`,
                      }}
                    >
                      {a.current_action}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
