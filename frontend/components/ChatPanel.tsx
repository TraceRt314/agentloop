"use client";

import { useEffect, useRef, useState } from "react";

interface ProjectBasic {
  id: string;
  name: string;
  slug: string;
}

interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export default function ChatPanel() {
  const [projects, setProjects] = useState<ProjectBasic[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [sessionId, setSessionId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Fetch projects on mount
  useEffect(() => {
    fetch("/api/v1/projects/")
      .then((r) => r.json())
      .then((data) => {
        setProjects(data || []);
        if (data?.length > 0) setSelectedProject(data[0].id);
      })
      .catch(() => {});
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setError(null);
    setSending(true);
    setInput("");

    // Optimistic user message
    const tempId = `temp-${Date.now()}`;
    setMessages((prev) => [...prev, { id: tempId, role: "user", content: text, created_at: new Date().toISOString() }]);

    try {
      const res = await fetch("/api/v1/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: text,
          project_id: selectedProject || undefined,
          session_id: sessionId || undefined,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();

      // Replace temp with real messages
      setMessages((prev) => {
        const without = prev.filter((m) => m.id !== tempId);
        return [
          ...without,
          { id: data.user_message.id, role: "user", content: data.user_message.content, created_at: data.user_message.created_at },
          { id: data.assistant_message.id, role: "assistant", content: data.assistant_message.content, created_at: data.assistant_message.created_at },
        ];
      });

      if (!sessionId) setSessionId(data.session_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== tempId));
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const startNewSession = () => {
    setSessionId("");
    setMessages([]);
    setError(null);
  };

  return (
    <div className="h-full flex flex-col p-4 gap-3">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <span className="ui-label text-blue-400">chat</span>
          <span className="text-slate-700 text-xs">|</span>
          <span className="text-[10px] text-slate-600">ai agent</span>
        </div>
        <button
          onClick={startNewSession}
          className="ui-label text-[9px] px-2 py-1 rounded border border-slate-700/40 text-slate-500 hover:text-slate-300 hover:border-slate-600 transition"
        >
          new session
        </button>
      </div>

      {/* Project selector */}
      <div className="shrink-0">
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          className="w-full px-3 py-1.5 rounded-md bg-slate-800/60 border border-slate-700/40 text-xs text-slate-300 outline-none focus:border-blue-500/40 transition"
        >
          <option value="">no project context</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} ({p.slug})
            </option>
          ))}
        </select>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-1">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-2">
              <div className="text-slate-700 text-2xl">&gt;_</div>
              <div className="ui-label text-slate-600">start a conversation</div>
              <div className="text-[10px] text-slate-700 max-w-[280px]">
                Ask questions about your projects, request code reviews, or get implementation guidance.
              </div>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`fade-in rounded-lg px-3 py-2 text-xs leading-relaxed ${
              msg.role === "user"
                ? "bg-blue-600/10 border border-blue-500/20 text-slate-300 ml-8"
                : "bg-slate-800/40 border border-slate-700/20 text-slate-400 mr-8"
            }`}
          >
            <div className="flex items-center gap-1.5 mb-1">
              <span className="ui-label" style={{ fontSize: 9, color: msg.role === "user" ? "#60a5fa" : "#a78bfa" }}>
                {msg.role === "user" ? "you" : "agent"}
              </span>
              <span className="text-slate-700" style={{ fontSize: 9 }}>
                {new Date(msg.created_at).toLocaleTimeString()}
              </span>
            </div>
            <div className="whitespace-pre-wrap">{msg.content}</div>
          </div>
        ))}

        {sending && (
          <div className="fade-in flex items-center gap-2 px-3 py-2 text-xs text-slate-600">
            <span className="animate-pulse">...</span>
            <span className="ui-label" style={{ fontSize: 9 }}>thinking</span>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="shrink-0 px-3 py-1.5 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-400">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="shrink-0 flex gap-2">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="ask something..."
          rows={2}
          disabled={sending}
          className="flex-1 px-3 py-2 rounded-md bg-slate-800/60 border border-slate-700/40 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/40 transition resize-none disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={sending || !input.trim()}
          className="px-4 rounded-md bg-blue-600/20 border border-blue-500/30 text-blue-400 ui-label hover:bg-blue-600/30 transition disabled:opacity-30 disabled:cursor-not-allowed self-end py-2"
        >
          send
        </button>
      </div>
    </div>
  );
}
