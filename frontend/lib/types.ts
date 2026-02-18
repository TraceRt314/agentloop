export interface AgentState {
  id: string;
  name: string;
  role: string;
  status: "active" | "paused";
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

// Office furniture/decoration positions
export interface OfficeFurniture {
  type: "desk" | "plant" | "server" | "whiteboard" | "coffee" | "bookshelf";
  x: number;
  y: number;
  width: number;
  height: number;
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

// Office layout - desk positions for each role
export const DESK_POSITIONS: Record<string, { x: number; y: number }> = {
  product_manager: { x: 120, y: 180 },
  developer: { x: 380, y: 180 },
  quality_assurance: { x: 120, y: 380 },
  deployer: { x: 380, y: 380 },
};

// Meeting point (center of office)
export const MEETING_POINT = { x: 250, y: 280 };

// Coffee machine
export const COFFEE_POINT = { x: 480, y: 80 };
