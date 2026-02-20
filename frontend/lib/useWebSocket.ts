"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import type { AgentState, WSMessage } from "./types";

const WS_URL = typeof window !== "undefined"
  ? (process.env.NEXT_PUBLIC_WS_URL || `ws://${window.location.hostname}:8080/api/v1/ws`)
  : "";

export function useAgentWebSocket() {
  const [agents, setAgents] = useState<AgentState[]>([]);
  const [events, setEvents] = useState<WSMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<NodeJS.Timeout>(undefined);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      reconnectRef.current = setTimeout(connect, 3000);
    };
    ws.onerror = () => ws.close();

    ws.onmessage = (e) => {
      let msg: WSMessage;
      try { msg = JSON.parse(e.data); } catch { return; }

      if (msg.type === "init" && msg.data.agents) {
        setAgents(msg.data.agents as unknown as AgentState[]);
      } else if (msg.type === "agent.update" || msg.type === "agent.action") {
        setAgents((prev) =>
          prev.map((a) =>
            a.id === (msg.data as { id: string }).id ? { ...a, ...msg.data } : a
          )
        );
      } else if (msg.type === "agent.batch_update" && Array.isArray(msg.data.agents)) {
        setAgents(msg.data.agents as unknown as AgentState[]);
      }

      if (msg.type !== "pong") {
        setEvents((prev) => [msg, ...prev].slice(0, 100));
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  // Fallback: poll REST API if WS not available
  useEffect(() => {
    if (connected) return;
    const poll = async () => {
      try {
        const res = await fetch("/api/v1/agents");
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) setAgents(data);
        }
      } catch { /* ignore */ }
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, [connected]);

  return { agents, events, connected };
}
