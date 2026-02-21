export interface AgentState {
  id: string;
  name: string;
  role: string;
  status: "active" | "paused";
  project_id: string;
  position_x: number;
  position_y: number;
  target_x: number;
  target_y: number;
  current_action: "idle" | "walking" | "working" | "talking" | "reviewing" | "thinking";
  avatar: string;
}

export interface WSMessage {
  type: string;
  data: Record<string, unknown>;
  ts: string;
}

export interface Mission {
  id: string;
  title: string;
  status: string;
  assigned_agent_id?: string;
}

export interface Step {
  id: string;
  title: string;
  status: string;
  step_type: string;
  claimed_by_agent_id?: string;
}

export interface EventItem {
  id: string;
  event_type: string;
  source_agent_id?: string;
  payload: Record<string, unknown>;
  created_at: string;
}

// Agent role → color mapping
export const ROLE_COLORS: Record<string, string> = {
  product_manager: "#fbbf24",
  developer: "#60a5fa",
  quality_assurance: "#4ade80",
  deployer: "#a78bfa",
  default: "#e94560",
};

// Agent role → emoji
export const ROLE_EMOJI: Record<string, string> = {
  product_manager: "📋",
  developer: "💻",
  quality_assurance: "🔍",
  deployer: "🚀",
};

