"use client";
import { useEffect, useRef, useState } from "react";
import type { AgentState } from "@/lib/types";
import { ROLE_COLORS, ROLE_EMOJI, DESK_POSITIONS } from "@/lib/types";

interface Props {
  agent: AgentState;
  scale?: number;
}

const ACTION_LABELS: Record<string, string> = {
  idle: "💤 Idle",
  walking: "🚶 Moving",
  working: "⚡ Working",
  talking: "💬 Talking",
  reviewing: "🔍 Reviewing",
  thinking: "🤔 Thinking",
};

export default function PixelAgent({ agent, scale = 1 }: Props) {
  const [frame, setFrame] = useState(0);
  const [displayX, setDisplayX] = useState(agent.position_x);
  const [displayY, setDisplayY] = useState(agent.position_y);
  const color = ROLE_COLORS[agent.role] ?? ROLE_COLORS.default;
  const emoji = ROLE_EMOJI[agent.role] ?? "🤖";

  // Smooth position interpolation
  useEffect(() => {
    const tx = agent.target_x || agent.position_x;
    const ty = agent.target_y || agent.position_y;
    let raf: number;
    const lerp = () => {
      setDisplayX((prev) => prev + (tx - prev) * 0.08);
      setDisplayY((prev) => prev + (ty - prev) * 0.08);
      raf = requestAnimationFrame(lerp);
    };
    raf = requestAnimationFrame(lerp);
    return () => cancelAnimationFrame(raf);
  }, [agent.position_x, agent.position_y, agent.target_x, agent.target_y]);

  // Animation frame cycling
  useEffect(() => {
    if (agent.current_action === "idle") return;
    const id = setInterval(() => setFrame((f) => (f + 1) % 4), 250);
    return () => clearInterval(id);
  }, [agent.current_action]);

  const isWorking = agent.current_action === "working";
  const isWalking = agent.current_action === "walking";

  return (
    <div
      className="absolute transition-none select-none"
      style={{
        left: `${displayX * scale}px`,
        top: `${displayY * scale}px`,
        zIndex: Math.floor(displayY),
        transform: `scale(${scale})`,
        transformOrigin: "top left",
      }}
    >
      {/* Shadow */}
      <div
        className="absolute rounded-full opacity-30"
        style={{
          width: 32,
          height: 8,
          background: "black",
          bottom: -2,
          left: 4,
        }}
      />

      {/* Body */}
      <div
        className={`relative ${isWalking ? "float-anim" : ""} ${isWorking ? "work-pulse" : ""}`}
        style={{ width: 40, height: 48 }}
      >
        {/* Head */}
        <div
          className="absolute rounded-md blink-anim"
          style={{
            width: 24,
            height: 24,
            left: 8,
            top: 0,
            background: "#fcd5b0",
            border: `2px solid ${color}`,
          }}
        >
          {/* Eyes */}
          <div className="absolute" style={{ top: 8, left: 4, width: 4, height: 4, background: "#333", borderRadius: 1 }} />
          <div className="absolute" style={{ top: 8, left: 14, width: 4, height: 4, background: "#333", borderRadius: 1 }} />
          {/* Mouth */}
          <div className="absolute" style={{ top: 15, left: 8, width: 6, height: 2, background: "#c97", borderRadius: 1 }} />
        </div>

        {/* Torso */}
        <div
          className="absolute rounded-sm"
          style={{
            width: 28,
            height: 18,
            left: 6,
            top: 22,
            background: color,
            border: "1px solid rgba(0,0,0,0.2)",
          }}
        />

        {/* Legs */}
        <div className="absolute flex gap-1" style={{ left: 10, top: 38 }}>
          <div
            className="rounded-sm"
            style={{
              width: 8,
              height: 10,
              background: "#445",
              transform: isWalking ? `translateY(${frame % 2 === 0 ? -2 : 2}px)` : "none",
            }}
          />
          <div
            className="rounded-sm"
            style={{
              width: 8,
              height: 10,
              background: "#445",
              transform: isWalking ? `translateY(${frame % 2 === 0 ? 2 : -2}px)` : "none",
            }}
          />
        </div>

        {/* Role emoji badge */}
        <div
          className="absolute text-sm"
          style={{ top: -16, left: 12 }}
        >
          {emoji}
        </div>

        {/* Action indicator */}
        {agent.current_action !== "idle" && (
          <div
            className="absolute ui-label text-center whitespace-nowrap"
            style={{
              top: -32,
              left: "50%",
              transform: "translateX(-50%)",
              fontSize: 7,
              color: color,
              textShadow: "1px 1px 0 #000",
            }}
          >
            {ACTION_LABELS[agent.current_action] ?? agent.current_action}
          </div>
        )}
      </div>

      {/* Name tag */}
      <div
        className="ui-label text-center mt-1 whitespace-nowrap"
        style={{
          fontSize: 7,
          color: "#fff",
          textShadow: "1px 1px 0 #000",
          width: 40,
        }}
      >
        {agent.name}
      </div>
    </div>
  );
}
