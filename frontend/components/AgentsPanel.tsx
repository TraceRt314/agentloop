"use client";

import { useCallback, useEffect, useState } from "react";

interface AgentData {
  id: string;
  name: string;
  role: string;
  description: string;
  status: "active" | "paused";
  config: Record<string, string>;
  current_action?: string;
}

interface AgentFormData {
  name: string;
  role: string;
  description: string;
  llm_provider: string;
  llm_model: string;
  llm_api_key: string;
  llm_base_url: string;
  thinking: string;
  system_prompt: string;
}

const ROLES = ["product_manager", "developer", "quality_assurance", "deployer", "security"];
const PROVIDERS = ["ollama", "openai", "openrouter", "openclaw"];
const THINKING_LEVELS = ["low", "medium", "high"];

const MODEL_PLACEHOLDERS: Record<string, string> = {
  ollama: "llama3.2",
  openai: "gpt-4o-mini",
  openrouter: "anthropic/claude-sonnet-4-6",
  openclaw: "dev-agent",
};

const ROLE_EMOJI: Record<string, string> = {
  product_manager: "\u{1F4CB}",
  developer: "\u{1F4BB}",
  quality_assurance: "\u{1F50D}",
  deployer: "\u{1F680}",
  security: "\u{1F6E1}",
};

const emptyForm: AgentFormData = {
  name: "",
  role: "developer",
  description: "",
  llm_provider: "",
  llm_model: "",
  llm_api_key: "",
  llm_base_url: "",
  thinking: "",
  system_prompt: "",
};

export default function AgentsPanel({ projectId }: { projectId: string }) {
  const [agents, setAgents] = useState<AgentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"list" | "form">("list");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<AgentFormData>({ ...emptyForm });
  const [saving, setSaving] = useState(false);

  const loadAgents = useCallback(async () => {
    if (!projectId) return;
    try {
      const r = await fetch(`/api/v1/agents/?project_id=${projectId}`);
      if (r.ok) setAgents(await r.json());
    } catch { /* ignore */ }
    setLoading(false);
  }, [projectId]);

  useEffect(() => {
    setLoading(true);
    loadAgents();
  }, [loadAgents]);

  const openCreate = () => {
    setEditingId(null);
    setForm({ ...emptyForm });
    setView("form");
  };

  const openEdit = (agent: AgentData) => {
    setEditingId(agent.id);
    setForm({
      name: agent.name,
      role: agent.role,
      description: agent.description,
      llm_provider: agent.config?.llm_provider || "",
      llm_model: agent.config?.llm_model || "",
      llm_api_key: agent.config?.llm_api_key || "",
      llm_base_url: agent.config?.llm_base_url || "",
      thinking: agent.config?.thinking || "",
      system_prompt: agent.config?.system_prompt || "",
    });
    setView("form");
  };

  const handleSave = async () => {
    setSaving(true);
    const config: Record<string, string> = {};
    if (form.llm_provider) config.llm_provider = form.llm_provider;
    if (form.llm_model) config.llm_model = form.llm_model;
    if (form.llm_api_key) config.llm_api_key = form.llm_api_key;
    if (form.llm_base_url) config.llm_base_url = form.llm_base_url;
    if (form.thinking) config.thinking = form.thinking;
    if (form.system_prompt) config.system_prompt = form.system_prompt;

    try {
      if (editingId) {
        await fetch(`/api/v1/agents/${editingId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: form.name,
            description: form.description,
            config,
          }),
        });
      } else {
        await fetch("/api/v1/agents/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: form.name,
            role: form.role,
            description: form.description || `${form.role} agent`,
            project_id: projectId,
            config,
          }),
        });
      }
      await loadAgents();
      setView("list");
    } catch { /* ignore */ }
    setSaving(false);
  };

  const toggleStatus = async (agent: AgentData) => {
    const newStatus = agent.status === "active" ? "paused" : "active";
    await fetch(`/api/v1/agents/${agent.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    await loadAgents();
  };

  const deleteAgent = async (id: string) => {
    await fetch(`/api/v1/agents/${id}`, { method: "DELETE" });
    await loadAgents();
  };

  const setField = (key: keyof AgentFormData, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="ui-label text-slate-600 animate-pulse">loading agents...</span>
      </div>
    );
  }

  // ── Form view ──
  if (view === "form") {
    const showApiKey = form.llm_provider && form.llm_provider !== "ollama";
    const showBaseUrl = form.llm_provider && !["ollama", "openai", "openrouter"].includes(form.llm_provider);

    return (
      <div className="p-6 max-w-2xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div className="ui-label text-slate-400">{editingId ? "edit agent" : "new agent"}</div>
          <button onClick={() => setView("list")} className="text-xs text-slate-600 hover:text-slate-400 transition">
            cancel
          </button>
        </div>

        <div className="space-y-4">
          {/* Name */}
          <div>
            <label className="ui-label text-slate-600 text-[10px] mb-1 block">name</label>
            <input
              value={form.name}
              onChange={(e) => setField("name", e.target.value)}
              placeholder="Agent name"
              className="w-full bg-slate-900/60 border border-slate-800/50 rounded px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500/40 transition"
            />
          </div>

          {/* Role */}
          <div>
            <label className="ui-label text-slate-600 text-[10px] mb-1 block">role</label>
            <select
              value={form.role}
              onChange={(e) => setField("role", e.target.value)}
              disabled={!!editingId}
              className="w-full bg-slate-900/60 border border-slate-800/50 rounded px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500/40 transition disabled:opacity-50"
            >
              {ROLES.map((r) => (
                <option key={r} value={r} className="bg-slate-900">
                  {ROLE_EMOJI[r] || ""} {r.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>

          {/* Description */}
          <div>
            <label className="ui-label text-slate-600 text-[10px] mb-1 block">description</label>
            <input
              value={form.description}
              onChange={(e) => setField("description", e.target.value)}
              placeholder="What this agent does"
              className="w-full bg-slate-900/60 border border-slate-800/50 rounded px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500/40 transition"
            />
          </div>

          <div className="border-t border-slate-800/30 pt-4">
            <div className="ui-label text-slate-500 text-[10px] mb-3">llm configuration (optional — empty = global default)</div>
          </div>

          {/* Provider + Model row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="ui-label text-slate-600 text-[10px] mb-1 block">provider</label>
              <select
                value={form.llm_provider}
                onChange={(e) => setField("llm_provider", e.target.value)}
                className="w-full bg-slate-900/60 border border-slate-800/50 rounded px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500/40 transition"
              >
                <option value="" className="bg-slate-900">default (global)</option>
                {PROVIDERS.map((p) => (
                  <option key={p} value={p} className="bg-slate-900">{p}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="ui-label text-slate-600 text-[10px] mb-1 block">model</label>
              <input
                value={form.llm_model}
                onChange={(e) => setField("llm_model", e.target.value)}
                placeholder={MODEL_PLACEHOLDERS[form.llm_provider] || "default"}
                className="w-full bg-slate-900/60 border border-slate-800/50 rounded px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500/40 transition"
              />
            </div>
          </div>

          {/* Thinking */}
          <div>
            <label className="ui-label text-slate-600 text-[10px] mb-1 block">thinking / reasoning</label>
            <select
              value={form.thinking}
              onChange={(e) => setField("thinking", e.target.value)}
              className="w-full bg-slate-900/60 border border-slate-800/50 rounded px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500/40 transition"
            >
              <option value="" className="bg-slate-900">default</option>
              {THINKING_LEVELS.map((t) => (
                <option key={t} value={t} className="bg-slate-900">{t}</option>
              ))}
            </select>
          </div>

          {/* API Key */}
          {showApiKey && (
            <div>
              <label className="ui-label text-slate-600 text-[10px] mb-1 block">api key</label>
              <input
                type="password"
                value={form.llm_api_key}
                onChange={(e) => setField("llm_api_key", e.target.value)}
                placeholder="sk-..."
                className="w-full bg-slate-900/60 border border-slate-800/50 rounded px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500/40 transition"
              />
            </div>
          )}

          {/* Base URL */}
          {showBaseUrl && (
            <div>
              <label className="ui-label text-slate-600 text-[10px] mb-1 block">base url</label>
              <input
                value={form.llm_base_url}
                onChange={(e) => setField("llm_base_url", e.target.value)}
                placeholder="https://api.example.com/v1"
                className="w-full bg-slate-900/60 border border-slate-800/50 rounded px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500/40 transition"
              />
            </div>
          )}

          {/* System Prompt */}
          <div>
            <label className="ui-label text-slate-600 text-[10px] mb-1 block">system prompt</label>
            <textarea
              value={form.system_prompt}
              onChange={(e) => setField("system_prompt", e.target.value)}
              placeholder="Custom instructions for this agent..."
              rows={3}
              className="w-full bg-slate-900/60 border border-slate-800/50 rounded px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500/40 transition resize-none"
            />
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={!form.name || saving}
          className="w-full py-2 rounded bg-blue-600/20 text-blue-400 ui-label text-sm hover:bg-blue-600/30 transition disabled:opacity-40"
        >
          {saving ? "saving..." : editingId ? "update agent" : "create agent"}
        </button>
      </div>
    );
  }

  // ── List view ──
  return (
    <div className="p-6 max-w-4xl mx-auto space-y-4">
      <div className="flex items-center justify-between mb-2">
        <div className="ui-label text-slate-500">agents ({agents.length})</div>
        <button
          onClick={openCreate}
          className="px-3 py-1.5 rounded bg-blue-600/20 text-blue-400 ui-label text-xs hover:bg-blue-600/30 transition"
        >
          + new agent
        </button>
      </div>

      {agents.length === 0 && (
        <div className="text-center py-12 text-slate-600 text-sm">
          no agents yet — create one to get started
        </div>
      )}

      <div className="space-y-2">
        {agents.map((agent) => {
          const provider = agent.config?.llm_provider || "default";
          const model = agent.config?.llm_model || "default";
          const paused = agent.status === "paused";

          return (
            <div
              key={agent.id}
              className={`px-4 py-3 rounded-md border ${
                paused ? "border-slate-800/30 bg-slate-800/10 opacity-60" : "border-slate-800/40 bg-slate-800/20"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg">{ROLE_EMOJI[agent.role] || "\u{1F916}"}</span>
                  <div>
                    <div className="text-sm text-slate-200">{agent.name}</div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="ui-label text-slate-600" style={{ fontSize: 9 }}>
                        {agent.role.replace("_", " ")}
                      </span>
                      <span className="text-slate-800">|</span>
                      <span className="ui-label text-slate-600" style={{ fontSize: 9 }}>
                        {provider}/{model}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`ui-label px-2 py-0.5 rounded text-[9px] ${
                      paused
                        ? "text-yellow-500 bg-yellow-500/10"
                        : "text-green-500 bg-green-500/10"
                    }`}
                  >
                    {agent.status}
                  </span>
                  <button
                    onClick={() => openEdit(agent)}
                    className="text-[10px] text-slate-600 hover:text-slate-400 transition ui-label px-2 py-1"
                  >
                    edit
                  </button>
                  <button
                    onClick={() => toggleStatus(agent)}
                    className="text-[10px] text-slate-600 hover:text-slate-400 transition ui-label px-2 py-1"
                  >
                    {paused ? "resume" : "pause"}
                  </button>
                  <button
                    onClick={() => deleteAgent(agent.id)}
                    className="text-[10px] text-red-800 hover:text-red-500 transition ui-label px-2 py-1"
                  >
                    delete
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
