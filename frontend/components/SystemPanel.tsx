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
    return (
      <div className="flex items-center justify-center h-64">
        <span className="ui-label text-slate-600 animate-pulse">checking systems...</span>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-8">
      {/* Services */}
      <div>
        <div className="ui-label text-slate-500 mb-3">services</div>
        <div className="grid grid-cols-3 gap-2">
          {Object.entries(services).map(([name, svc]) => {
            const ok = svc.status === "healthy";
            return (
              <div
                key={name}
                className={`px-3 py-2.5 rounded-md border ${
                  ok ? "border-green-500/15 bg-green-500/5" : "border-red-500/15 bg-red-500/5"
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`} />
                  <span className="text-xs text-slate-300">
                    {name.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="text-[10px] text-slate-600 truncate">{svc.url}</div>
              </div>
            );
          })}
        </div>
      </div>

      {overview && (
        <>
          {/* Stats */}
          <div>
            <div className="ui-label text-slate-500 mb-3">stats</div>
            <div className="grid grid-cols-4 gap-2">
              {[
                { label: "agents", value: overview.agents.length, color: "#3b82f6" },
                { label: "projects", value: overview.projects.length, color: "#22c55e" },
                { label: "missions", value: overview.missions.active, color: "#eab308" },
                { label: "proposals", value: overview.proposals.pending, color: "#a78bfa" },
              ].map((s) => (
                <div key={s.label} className="px-3 py-2.5 rounded-md border border-slate-800/40 bg-slate-800/20">
                  <div className="text-xl font-medium" style={{ color: s.color }}>{s.value}</div>
                  <div className="ui-label text-slate-600 mt-0.5" style={{ fontSize: 9 }}>{s.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Projects */}
          <div>
            <div className="ui-label text-slate-500 mb-3">projects</div>
            <div className="grid grid-cols-3 gap-2">
              {overview.projects.map((p) => (
                <div key={p.slug} className="px-3 py-2 rounded-md border border-slate-800/30 bg-slate-800/10">
                  <div className="text-xs text-slate-300">{p.name}</div>
                  <div className="ui-label text-slate-700 mt-0.5" style={{ fontSize: 9 }}>{p.slug}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Agent activity */}
          <div>
            <div className="ui-label text-slate-500 mb-3">agent activity</div>
            <div className="grid grid-cols-4 gap-2">
              {overview.agents.map((a) => {
                const colors: Record<string, string> = {
                  idle: "#64748b", working: "#22c55e", walking: "#3b82f6",
                  thinking: "#eab308", talking: "#a78bfa", reviewing: "#ef4444",
                };
                const c = colors[a.current_action] ?? "#64748b";
                return (
                  <div key={a.name} className="px-3 py-2 rounded-md border border-slate-800/30 bg-slate-800/10 text-center">
                    <div className="text-xs text-slate-300">{a.name}</div>
                    <div className="text-[10px] text-slate-600 mt-0.5">{a.role.replace("_", " ")}</div>
                    <div
                      className="ui-label mt-1.5 px-2 py-0.5 rounded inline-block"
                      style={{ fontSize: 8, color: c, background: `${c}12` }}
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
