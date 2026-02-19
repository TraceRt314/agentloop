"use client";
import type { AgentState } from "@/lib/types";
import { ROLE_COLORS, ROLE_EMOJI } from "@/lib/types";

interface Props {
  agents: AgentState[];
  connected: boolean;
}

const ACTION_LABELS: Record<string, string> = {
  idle: "idle",
  walking: "moving",
  working: "working",
  talking: "talking",
  reviewing: "review",
  thinking: "think",
};

export default function StatusPanel({ agents, connected }: Props) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-slate-800/30">
        <span className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`} />
        <span className="ui-label text-slate-500">{connected ? "connected" : "offline"}</span>
      </div>

      <div className="ui-label text-slate-600 px-1">agents</div>

      <div className="space-y-1.5">
        {agents.map((agent) => {
          const color = ROLE_COLORS[agent.role] ?? ROLE_COLORS.default;
          const emoji = ROLE_EMOJI[agent.role] ?? ">";
          const isWorking = agent.current_action === "working";
          return (
            <div
              key={agent.id}
              className={`px-2.5 py-2 rounded-md border transition-all ${isWorking ? "work-pulse" : ""}`}
              style={{
                background: `${color}06`,
                borderColor: `${color}18`,
              }}
            >
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-sm">{emoji}</span>
                <span className="text-xs font-medium" style={{ color }}>
                  {agent.name}
                </span>
                <span
                  className={`ml-auto w-1.5 h-1.5 rounded-full ${
                    agent.status === "active" ? "bg-green-500" : "bg-slate-700"
                  }`}
                />
              </div>
              <div className="flex items-center justify-between pl-6">
                <span className="text-[10px] text-slate-600">{agent.role.replace("_", " ")}</span>
                <span
                  className="ui-label text-[8px] px-1.5 py-0.5 rounded"
                  style={{ background: `${color}12`, color }}
                >
                  {ACTION_LABELS[agent.current_action] ?? agent.current_action}
                </span>
              </div>
            </div>
          );
        })}
        {agents.length === 0 && (
          <p className="text-slate-700 text-xs px-1">no agents registered</p>
        )}
      </div>
    </div>
  );
}
