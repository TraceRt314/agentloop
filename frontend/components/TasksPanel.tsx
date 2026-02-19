"use client";

import { useEffect, useState } from "react";
import { ROLE_COLORS } from "@/lib/types";

interface MCBoard {
  id: string;
  name: string;
  description: string;
  project_slug: string;
  task_count: number;
  status_counts: Record<string, number>;
}

interface MCTask {
  id: string;
  title: string;
  description?: string;
  priority: string;
  status: string;
}

const PRIORITY_COLORS: Record<string, string> = {
  high: "#f87171",
  medium: "#fbbf24",
  low: "#4ade80",
};

const STATUS_ICONS: Record<string, string> = {
  inbox: "📥",
  in_progress: "⚡",
  done: "✅",
  cancelled: "❌",
};

export default function TasksPanel() {
  const [boards, setBoards] = useState<MCBoard[]>([]);
  const [selectedBoard, setSelectedBoard] = useState<string | null>(null);
  const [tasks, setTasks] = useState<MCTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingTasks, setLoadingTasks] = useState(false);

  // Fetch boards
  useEffect(() => {
    fetch("/api/v1/dashboard/mc/boards")
      .then((r) => r.json())
      .then((d) => {
        setBoards(d.boards || []);
        setLoading(false);
        if (d.boards?.length > 0) setSelectedBoard(d.boards[0].id);
      })
      .catch(() => setLoading(false));
  }, []);

  // Fetch tasks when board selected
  useEffect(() => {
    if (!selectedBoard) return;
    setLoadingTasks(true);
    fetch(`/api/v1/dashboard/mc/boards/${selectedBoard}/tasks`)
      .then((r) => r.json())
      .then((d) => {
        setTasks(d.tasks || []);
        setLoadingTasks(false);
      })
      .catch(() => setLoadingTasks(false));
  }, [selectedBoard]);

  if (loading) {
    return <div className="p-6 text-center text-slate-600 ui-label text-xs animate-pulse">Loading boards...</div>;
  }

  return (
    <div className="flex h-full">
      {/* Board list */}
      <div className="w-56 border-r border-slate-800/50 p-3 space-y-1.5 overflow-y-auto">
        <h3 className="ui-label text-[9px] text-slate-500 uppercase tracking-wider mb-3">📋 MC Boards</h3>
        {boards.map((b) => (
          <button
            key={b.id}
            onClick={() => setSelectedBoard(b.id)}
            className={`w-full text-left px-3 py-2.5 rounded-lg border transition-all ${
              selectedBoard === b.id
                ? "bg-blue-500/10 border-blue-500/30 text-white"
                : "bg-slate-800/30 border-slate-700/20 text-slate-400 hover:bg-slate-800/50"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium truncate">{b.name}</span>
              <span className="ui-label text-slate-500 shrink-0 ml-2" style={{ fontSize: 8 }}>
                {b.task_count}
              </span>
            </div>
            <div className="flex gap-1 mt-1.5">
              {Object.entries(b.status_counts).map(([status, count]) => (
                <span
                  key={status}
                  className="px-1.5 py-0.5 rounded text-slate-500"
                  style={{ fontSize: 7, background: "rgba(255,255,255,0.05)" }}
                >
                  {STATUS_ICONS[status] ?? "•"} {count}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>

      {/* Task list */}
      <div className="flex-1 p-4 overflow-y-auto">
        {loadingTasks ? (
          <div className="text-center text-slate-600 ui-label text-xs animate-pulse mt-8">Loading tasks...</div>
        ) : tasks.length === 0 ? (
          <div className="text-center text-slate-700 text-xs mt-8">No tasks in this board</div>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center justify-between mb-4">
              <h3 className="ui-label text-xs text-slate-400">
                {boards.find((b) => b.id === selectedBoard)?.name ?? "Tasks"}
              </h3>
              <span className="ui-label text-slate-600" style={{ fontSize: 8 }}>{tasks.length} tasks</span>
            </div>
            {tasks.map((task) => (
              <div
                key={task.id}
                className="p-3 rounded-lg border border-slate-700/30 bg-slate-800/30 hover:bg-slate-800/50 transition-all group"
              >
                <div className="flex items-start gap-3">
                  <span className="text-sm mt-0.5">{STATUS_ICONS[task.status] ?? "📌"}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-slate-200 group-hover:text-white transition">{task.title}</span>
                    </div>
                    {task.description && (
                      <p className="text-xs text-slate-500 mt-1 line-clamp-2">{task.description}</p>
                    )}
                    <div className="flex items-center gap-2 mt-2">
                      <span
                        className="px-2 py-0.5 rounded-full text-xs font-medium"
                        style={{
                          fontSize: 9,
                          color: PRIORITY_COLORS[task.priority] ?? "#8892b0",
                          background: `${PRIORITY_COLORS[task.priority] ?? "#8892b0"}15`,
                        }}
                      >
                        {task.priority}
                      </span>
                      <span className="text-slate-600" style={{ fontSize: 9 }}>{task.status}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
