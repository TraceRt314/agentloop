"use client";
import type { AgentState } from "@/lib/types";
import { ROLE_COLORS, ROLE_EMOJI } from "@/lib/types";

interface Props {
  agents: AgentState[];
  connected: boolean;
}

export default function StatusPanel({ agents, connected }: Props) {
  return (
    <div className="space-y-4">
      {/* Connection status */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/30">
        <span
          className={`w-2 h-2 rounded-full ${connected ? "bg-green-500 animate-pulse" : "bg-red-500"}`}
        />
        <span className="pixel-font text-xs text-slate-400">
          {connected ? "CONNECTED" : "OFFLINE"}
        </span>
      </div>

      {/* Agent cards */}
      <h3 className="pixel-font text-xs text-slate-400">AGENTS</h3>
      <div className="space-y-2">
        {agents.map((agent) => {
          const color = ROLE_COLORS[agent.role] ?? ROLE_COLORS.default;
          const emoji = ROLE_EMOJI[agent.role] ?? "🤖";
          return (
            <div
              key={agent.id}
              className="p-3 rounded-lg border transition-all"
              style={{
                background: `${color}08`,
                borderColor: `${color}30`,
              }}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-base">{emoji}</span>
                <span className="pixel-font text-xs" style={{ color }}>
                  {agent.name}
                </span>
                <span
                  className={`ml-auto w-2 h-2 rounded-full ${
                    agent.status === "active" ? "bg-green-500" : "bg-slate-600"
                  }`}
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">{agent.role.replace("_", " ")}</span>
                <span
                  className="pixel-font px-2 py-0.5 rounded text-xs"
                  style={{
                    fontSize: 7,
                    background: `${color}20`,
                    color,
                  }}
                >
                  {agent.current_action}
                </span>
              </div>
            </div>
          );
        })}
        {agents.length === 0 && (
          <p className="text-slate-600 text-xs pixel-font">No agents registered</p>
        )}
      </div>
    </div>
  );
}
