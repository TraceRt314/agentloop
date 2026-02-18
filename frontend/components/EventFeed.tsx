"use client";
import type { WSMessage } from "@/lib/types";

interface Props {
  events: WSMessage[];
}

const EVENT_ICONS: Record<string, string> = {
  "init": "🔌",
  "agent.update": "🤖",
  "agent.action": "⚡",
  "step.completed": "✅",
  "step.failed": "❌",
  "mission.completed": "🎯",
  "proposal.approved": "👍",
  "proposal.rejected": "👎",
  "trigger.fired": "🔔",
  "pong": "💓",
};

function formatTime(ts: string) {
  try {
    return new Date(ts).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return ts;
  }
}

export default function EventFeed({ events }: Props) {
  return (
    <div className="h-full flex flex-col">
      <h3 className="pixel-font text-xs text-slate-400 mb-3 flex items-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full bg-green-500 animate-pulse" />
        LIVE FEED
      </h3>
      <div className="flex-1 overflow-y-auto space-y-1 pr-1 scrollbar-thin">
        {events.length === 0 && (
          <p className="text-slate-600 text-xs pixel-font">Waiting for events...</p>
        )}
        {events.map((ev, i) => (
          <div
            key={i}
            className="flex items-start gap-2 px-2 py-1.5 rounded bg-slate-800/50 border border-slate-700/30 text-xs"
          >
            <span className="text-sm shrink-0">{EVENT_ICONS[ev.type] ?? "📡"}</span>
            <div className="min-w-0 flex-1">
              <span className="text-slate-300 font-mono">{ev.type}</span>
              {ev.data && typeof ev.data === "object" && "name" in ev.data && (
                <span className="text-slate-500 ml-1">→ {String(ev.data.name)}</span>
              )}
            </div>
            <span className="text-slate-600 shrink-0 pixel-font" style={{ fontSize: 6 }}>
              {formatTime(ev.ts)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
