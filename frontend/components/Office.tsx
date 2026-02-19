"use client";
import type { AgentState } from "@/lib/types";
import { DESK_POSITIONS, MEETING_POINT, COFFEE_POINT } from "@/lib/types";
import PixelAgent from "./PixelAgent";

interface Props {
  agents: AgentState[];
  width?: number;
  height?: number;
}

function Desk({ x, y, label }: { x: number; y: number; label: string }) {
  return (
    <div className="absolute" style={{ left: x - 24, top: y - 10 }}>
      {/* Desk surface */}
      <div
        className="rounded-sm"
        style={{
          width: 64,
          height: 32,
          background: "linear-gradient(135deg, #8B6914 0%, #A67C00 50%, #8B6914 100%)",
          border: "2px solid #6B4F12",
          boxShadow: "0 4px 0 #5a3e10",
        }}
      />
      {/* Monitor */}
      <div className="absolute" style={{ top: -20, left: 20 }}>
        <div
          style={{
            width: 24,
            height: 18,
            background: "#1e293b",
            border: "2px solid #475569",
            borderRadius: 2,
          }}
        >
          <div
            className="rounded-sm"
            style={{
              width: 16,
              height: 10,
              margin: "2px auto",
              background: agent_action_to_screen_color("working"),
            }}
          />
        </div>
        {/* Stand */}
        <div style={{ width: 4, height: 4, background: "#475569", margin: "0 auto" }} />
      </div>
      {/* Label */}
      <div
        className="ui-label text-center mt-1"
        style={{ fontSize: 6, color: "#8892b0" }}
      >
        {label}
      </div>
    </div>
  );
}

function agent_action_to_screen_color(action: string) {
  switch (action) {
    case "working": return "#4ade80";
    case "reviewing": return "#60a5fa";
    case "thinking": return "#fbbf24";
    default: return "#334155";
  }
}

function Plant({ x, y }: { x: number; y: number }) {
  return (
    <div className="absolute" style={{ left: x, top: y }}>
      <div style={{ fontSize: 20 }}>🌿</div>
    </div>
  );
}

function CoffeeMachine({ x, y }: { x: number; y: number }) {
  return (
    <div className="absolute" style={{ left: x, top: y }}>
      <div style={{ fontSize: 18 }}>☕</div>
      <div className="ui-label" style={{ fontSize: 5, color: "#8892b0", textAlign: "center" }}>Coffee</div>
    </div>
  );
}

function ServerRack({ x, y }: { x: number; y: number }) {
  return (
    <div className="absolute" style={{ left: x, top: y }}>
      <div
        style={{
          width: 28,
          height: 40,
          background: "linear-gradient(180deg, #1e293b 0%, #0f172a 100%)",
          border: "2px solid #334155",
          borderRadius: 3,
          padding: 3,
        }}
      >
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-1 mb-1">
            <div
              className="rounded-full"
              style={{
                width: 4,
                height: 4,
                background: i < 2 ? "#4ade80" : "#334155",
                boxShadow: i < 2 ? "0 0 4px #4ade80" : "none",
              }}
            />
            <div style={{ width: 14, height: 3, background: "#334155", borderRadius: 1 }} />
          </div>
        ))}
      </div>
      <div className="ui-label" style={{ fontSize: 5, color: "#8892b0", textAlign: "center", marginTop: 2 }}>Server</div>
    </div>
  );
}

function Whiteboard({ x, y }: { x: number; y: number }) {
  return (
    <div className="absolute" style={{ left: x, top: y }}>
      <div
        style={{
          width: 80,
          height: 50,
          background: "#f8fafc",
          border: "3px solid #94a3b8",
          borderRadius: 2,
          padding: 4,
        }}
      >
        <div style={{ width: "60%", height: 3, background: "#e94560", marginBottom: 4, borderRadius: 1 }} />
        <div style={{ width: "80%", height: 2, background: "#60a5fa", marginBottom: 3, borderRadius: 1 }} />
        <div style={{ width: "45%", height: 2, background: "#4ade80", marginBottom: 3, borderRadius: 1 }} />
        <div style={{ width: "70%", height: 2, background: "#fbbf24", borderRadius: 1 }} />
      </div>
      <div className="ui-label" style={{ fontSize: 5, color: "#8892b0", textAlign: "center", marginTop: 2 }}>Sprint Board</div>
    </div>
  );
}

function Floor({ width, height }: { width: number; height: number }) {
  const tiles = [];
  const tileSize = 32;
  for (let x = 0; x < width; x += tileSize) {
    for (let y = 0; y < height; y += tileSize) {
      const isDark = ((x / tileSize) + (y / tileSize)) % 2 === 0;
      tiles.push(
        <div
          key={`${x}-${y}`}
          className="absolute"
          style={{
            left: x,
            top: y,
            width: tileSize,
            height: tileSize,
            background: isDark ? "#1e2a3a" : "#1a2435",
            borderRight: "1px solid #2a3a4f10",
            borderBottom: "1px solid #2a3a4f10",
          }}
        />
      );
    }
  }
  return <>{tiles}</>;
}

export default function Office({ agents, width = 560, height = 500 }: Props) {
  return (
    <div
      className="relative overflow-hidden rounded-xl border-2 border-slate-700"
      style={{
        width,
        height,
        background: "#141d2f",
        boxShadow: "inset 0 0 60px rgba(0,0,0,0.5)",
      }}
    >
      {/* Floor */}
      <Floor width={width} height={height} />

      {/* Walls */}
      <div
        className="absolute"
        style={{
          left: 0,
          top: 0,
          width: "100%",
          height: 40,
          background: "linear-gradient(180deg, #2a3a50 0%, #1e2d42 100%)",
          borderBottom: "3px solid #3a4f6f",
        }}
      />

      {/* Window */}
      <div className="absolute" style={{ left: 200, top: 4 }}>
        <div
          style={{
            width: 80,
            height: 30,
            background: "linear-gradient(180deg, #1e40af 0%, #3b82f6 40%, #93c5fd 100%)",
            border: "2px solid #64748b",
            borderRadius: 2,
          }}
        />
      </div>

      {/* Furniture */}
      <Whiteboard x={10} y={55} />
      <ServerRack x={510} y={60} />
      <CoffeeMachine x={COFFEE_POINT.x} y={COFFEE_POINT.y} />
      <Plant x={10} y={460} />
      <Plant x={520} y={440} />

      {/* Desks */}
      {Object.entries(DESK_POSITIONS).map(([role, pos]) => (
        <Desk key={role} x={pos.x} y={pos.y} label={role.replace("_", " ").toUpperCase()} />
      ))}

      {/* Meeting table (center) */}
      <div
        className="absolute rounded-full"
        style={{
          left: MEETING_POINT.x - 20,
          top: MEETING_POINT.y - 10,
          width: 40,
          height: 20,
          background: "linear-gradient(135deg, #6B4F12 0%, #8B6914 100%)",
          border: "2px solid #5a3e10",
          boxShadow: "0 2px 0 #4a2e08",
        }}
      />

      {/* Agents */}
      {agents.map((agent) => (
        <PixelAgent key={agent.id} agent={agent} />
      ))}

      {/* Room label */}
      <div
        className="absolute ui-label"
        style={{
          bottom: 8,
          left: "50%",
          transform: "translateX(-50%)",
          fontSize: 8,
          color: "#4a5568",
          letterSpacing: 2,
        }}
      >
        🏢 AGENTLOOP HQ
      </div>
    </div>
  );
}
