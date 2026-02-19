"use client";
import type { WSMessage } from "@/lib/types";

interface Props {
  events: WSMessage[];
}

const EVENT_SYMBOLS: Record<string, string> = {
  "init": "--",
  "agent.update": ">>",
  "agent.action": "->",
  "agent.batch_update": "=>",
  "step.completed": "ok",
  "step.failed": "!!",
  "mission.completed": "**",
  "proposal.approved": "++",
  "proposal.rejected": "--",
  "trigger.fired": "~~",
  "pong": "..",
};

function formatTime(ts: string) {
  try {
    return new Date(ts).toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

export default function EventFeed({ events }: Props) {
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 mb-2">
        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
        <span className="ui-label text-slate-500">live feed</span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-0.5 pr-1">
        {events.length === 0 && (
          <p className="text-slate-700 text-xs">waiting for events...</p>
        )}
        {events.map((ev, i) => (
          <div
            key={i}
            className="flex items-start gap-2 px-2 py-1 rounded hover:bg-slate-800/30 transition text-[11px]"
          >
            <span className="ui-label text-slate-600 shrink-0 w-5 text-center" style={{ fontSize: 9 }}>
              {EVENT_SYMBOLS[ev.type] ?? ">>"}
            </span>
            <div className="min-w-0 flex-1">
              <span className="text-slate-400">{ev.type}</span>
              {ev.data && typeof ev.data === "object" && "name" in ev.data && (
                <span className="text-slate-600 ml-1">{String(ev.data.name)}</span>
              )}
            </div>
            <span className="text-slate-700 shrink-0" style={{ fontSize: 9 }}>
              {formatTime(ev.ts)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
