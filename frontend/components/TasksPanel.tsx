"use client";

import { useEffect, useState, useRef } from "react";

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

interface AgentBasic {
  id: string;
  name: string;
  role: string;
}

interface ProjectBasic {
  id: string;
  name: string;
  slug: string;
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f87171",
  medium: "#eab308",
  low: "#22c55e",
};

const STATUS_STYLES: Record<string, { icon: string; color: string }> = {
  inbox: { icon: ">>", color: "#64748b" },
  in_progress: { icon: "~>", color: "#3b82f6" },
  review: { icon: "?!", color: "#a78bfa" },
  done: { icon: "ok", color: "#22c55e" },
  cancelled: { icon: "xx", color: "#ef4444" },
};

export default function TasksPanel() {
  const [boards, setBoards] = useState<MCBoard[]>([]);
  const [selectedBoard, setSelectedBoard] = useState<string | null>(null);
  const [tasks, setTasks] = useState<MCTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingTasks, setLoadingTasks] = useState(false);

  // Add-task form state
  const [showForm, setShowForm] = useState(false);
  const [formTitle, setFormTitle] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formPriority, setFormPriority] = useState("medium");
  const [submitting, setSubmitting] = useState(false);
  const [agents, setAgents] = useState<AgentBasic[]>([]);
  const [projects, setProjects] = useState<ProjectBasic[]>([]);
  const titleRef = useRef<HTMLInputElement>(null);

  // Fetch boards
  useEffect(() => {
    fetch("/api/v1/mc/boards")
      .then((r) => r.json())
      .then((d) => {
        setBoards(d.boards || []);
        setLoading(false);
        if (d.boards?.length > 0) setSelectedBoard(d.boards[0].id);
      })
      .catch(() => setLoading(false));

    // Also fetch agents + projects for the add-task form
    fetch("/api/v1/dashboard/overview")
      .then((r) => r.json())
      .then((d) => {
        setAgents(d.agents || []);
        setProjects(d.projects || []);
      })
      .catch(() => {});
  }, []);

  // Fetch tasks when board selected
  useEffect(() => {
    if (!selectedBoard) return;
    setLoadingTasks(true);
    fetch(`/api/v1/mc/boards/${selectedBoard}/tasks`)
      .then((r) => r.json())
      .then((d) => {
        setTasks(d.tasks || []);
        setLoadingTasks(false);
      })
      .catch(() => setLoadingTasks(false));
  }, [selectedBoard]);

  // Focus title input when form opens
  useEffect(() => {
    if (showForm) titleRef.current?.focus();
  }, [showForm]);

  const handleCreateTask = async () => {
    if (!formTitle.trim() || agents.length === 0 || projects.length === 0) return;
    setSubmitting(true);

    try {
      const res = await fetch("/api/v1/proposals/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: formTitle.trim(),
          description: formDesc.trim() || formTitle.trim(),
          rationale: "Created from AgentLoop UI",
          priority: formPriority,
          auto_approve: formPriority === "critical" || formPriority === "high",
          agent_id: agents[0].id,
          project_id: projects[0].id,
        }),
      });

      if (res.ok) {
        setFormTitle("");
        setFormDesc("");
        setFormPriority("medium");
        setShowForm(false);
      }
    } catch {
      // silently fail — user sees no change
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="ui-label text-slate-600 animate-pulse">loading boards...</span>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Sidebar — board list */}
      <div className="w-52 shrink-0 border-r border-slate-800/40 p-3 flex flex-col gap-1.5 overflow-y-auto">
        <div className="ui-label text-slate-600 mb-2">boards</div>
        {boards.map((b) => (
          <button
            key={b.id}
            onClick={() => setSelectedBoard(b.id)}
            className={`w-full text-left px-3 py-2 rounded-md border transition-all ${
              selectedBoard === b.id
                ? "bg-blue-500/10 border-blue-500/20 text-blue-300"
                : "bg-transparent border-transparent text-slate-500 hover:text-slate-300 hover:bg-slate-800/40"
            }`}
          >
            <div className="text-xs font-medium truncate">{b.name}</div>
            <div className="flex gap-2 mt-1">
              {Object.entries(b.status_counts).map(([st, count]) => (
                <span key={st} className="text-[10px] text-slate-600">
                  {STATUS_STYLES[st]?.icon ?? "."}{count}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>

      {/* Main task list */}
      <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
        {/* Header with add button */}
        <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-slate-800/40">
          <div className="flex items-center gap-3">
            <span className="ui-label text-slate-400">
              {boards.find((b) => b.id === selectedBoard)?.name ?? "tasks"}
            </span>
            <span className="text-[10px] text-slate-700">{tasks.length} items</span>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className={`ui-label px-3 py-1 rounded-md border transition-all ${
              showForm
                ? "bg-red-500/10 border-red-500/20 text-red-400"
                : "bg-blue-500/10 border-blue-500/20 text-blue-400 hover:bg-blue-500/20"
            }`}
          >
            {showForm ? "cancel" : "+ new task"}
          </button>
        </div>

        {/* Add task form */}
        {showForm && (
          <div className="shrink-0 px-4 py-3 border-b border-slate-800/40 bg-slate-900/40 fade-in">
            <div className="space-y-2">
              <input
                ref={titleRef}
                type="text"
                placeholder="task title..."
                value={formTitle}
                onChange={(e) => setFormTitle(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleCreateTask()}
                className="w-full px-3 py-2 rounded-md bg-slate-800/60 border border-slate-700/40 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/40 transition"
              />
              <textarea
                placeholder="description (optional)..."
                value={formDesc}
                onChange={(e) => setFormDesc(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 rounded-md bg-slate-800/60 border border-slate-700/40 text-xs text-slate-300 placeholder-slate-600 outline-none focus:border-blue-500/40 transition resize-none"
              />
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="ui-label text-slate-600 text-[9px]">priority:</span>
                  {["low", "medium", "high", "critical"].map((p) => (
                    <button
                      key={p}
                      onClick={() => setFormPriority(p)}
                      className={`ui-label px-2 py-0.5 rounded text-[9px] border transition-all ${
                        formPriority === p
                          ? "border-current"
                          : "border-transparent opacity-40 hover:opacity-70"
                      }`}
                      style={{ color: PRIORITY_COLORS[p] }}
                    >
                      {p}
                    </button>
                  ))}
                </div>
                <button
                  onClick={handleCreateTask}
                  disabled={!formTitle.trim() || submitting}
                  className="ui-label px-4 py-1.5 rounded-md bg-blue-600/20 border border-blue-500/30 text-blue-400 hover:bg-blue-600/30 transition disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  {submitting ? "creating..." : "create proposal"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Scrollable task list */}
        <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3">
          {loadingTasks ? (
            <div className="flex items-center justify-center h-32">
              <span className="ui-label text-slate-600 animate-pulse">loading tasks...</span>
            </div>
          ) : tasks.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <span className="text-xs text-slate-700">no tasks on this board</span>
            </div>
          ) : (
            <div className="space-y-1.5">
              {tasks.map((task) => {
                const style = STATUS_STYLES[task.status] ?? STATUS_STYLES.inbox;
                return (
                  <div
                    key={task.id}
                    className="group px-3 py-2.5 rounded-md border border-slate-800/30 hover:border-slate-700/40 hover:bg-slate-800/20 transition-all"
                  >
                    <div className="flex items-start gap-3">
                      <span
                        className="ui-label shrink-0 mt-0.5 w-6 text-center"
                        style={{ color: style.color, fontSize: 9 }}
                      >
                        {style.icon}
                      </span>
                      <div className="flex-1 min-w-0">
                        <span className="text-[13px] text-slate-300 group-hover:text-slate-100 transition">
                          {task.title}
                        </span>
                        {task.description && (
                          <p className="text-[11px] text-slate-600 mt-0.5 line-clamp-2 leading-relaxed">
                            {task.description}
                          </p>
                        )}
                      </div>
                      <div className="shrink-0 flex items-center gap-2">
                        <span
                          className="ui-label text-[9px] px-1.5 py-0.5 rounded"
                          style={{
                            color: PRIORITY_COLORS[task.priority] ?? "#64748b",
                            background: `${PRIORITY_COLORS[task.priority] ?? "#64748b"}12`,
                          }}
                        >
                          {task.priority}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
