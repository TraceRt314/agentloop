"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

interface ProjectBasic {
  id: string;
  name: string;
  slug: string;
}

interface AgentBasic {
  id: string;
  name: string;
  role: string;
}

interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  agent_name?: string;
}

interface ChatSession {
  session_id: string;
  project_id: string | null;
  message_count: number;
  last_message_at: string | null;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
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
  const abortRef = useRef<AbortController | null>(null);

  // Sidebar
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  // Context badge
  const [knowledgeCount, setKnowledgeCount] = useState<number | null>(null);

  // Agent routing
  const [agents, setAgents] = useState<AgentBasic[]>([]);
  const [showMentions, setShowMentions] = useState(false);
  const [mentionFilter, setMentionFilter] = useState("");

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

  // Fetch agents when project changes
  useEffect(() => {
    if (!selectedProject) {
      setAgents([]);
      return;
    }
    fetch(`/api/v1/agents/?project_id=${selectedProject}`)
      .then((r) => r.json())
      .then((data) => setAgents(data || []))
      .catch(() => setAgents([]));
  }, [selectedProject]);

  // Fetch sessions when sidebar opens
  const refreshSessions = useCallback(() => {
    const url = selectedProject
      ? `/api/v1/chat/sessions?project_id=${selectedProject}`
      : "/api/v1/chat/sessions";
    fetch(url)
      .then((r) => r.json())
      .then((data) => setSessions(data || []))
      .catch(() => {});
  }, [selectedProject]);

  useEffect(() => {
    if (sidebarOpen) refreshSessions();
  }, [sidebarOpen, refreshSessions]);

  // Cleanup stream on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setError(null);
    setSending(true);
    setInput("");

    // Optimistic user message
    const tempUserId = `temp-user-${Date.now()}`;
    const tempAssistantId = `temp-assistant-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      {
        id: tempUserId,
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
      },
      {
        id: tempAssistantId,
        role: "assistant",
        content: "",
        created_at: new Date().toISOString(),
      },
    ]);

    try {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch("/api/v1/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: text,
          project_id: selectedProject || undefined,
          session_id: sessionId || undefined,
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          let event: {
            type: string;
            session_id?: string;
            content?: string;
            message_id?: string;
            agent_name?: string;
            project?: string;
            knowledge_count?: number;
          };
          try {
            event = JSON.parse(raw);
          } catch {
            continue;
          }

          if (event.type === "start" && event.session_id) {
            if (!sessionId) setSessionId(event.session_id);
          } else if (event.type === "context") {
            setKnowledgeCount(event.knowledge_count ?? null);
          } else if (event.type === "token" && event.content) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? { ...m, content: m.content + event.content }
                  : m
              )
            );
          } else if (event.type === "done") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? {
                      ...m,
                      id: event.message_id || m.id,
                      agent_name: event.agent_name,
                    }
                  : m
              )
            );
          } else if (event.type === "error") {
            setError(event.content || "Stream error");
          }
        }
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
      // Remove optimistic messages on error
      setMessages((prev) =>
        prev.filter(
          (m) => m.id !== tempUserId && m.id !== tempAssistantId
        )
      );
    } finally {
      setSending(false);
      abortRef.current = null;
      inputRef.current?.focus();
      if (sidebarOpen) refreshSessions();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setInput(val);

    // Detect @mention trigger
    const lastAt = val.lastIndexOf("@");
    if (lastAt !== -1 && (lastAt === 0 || val[lastAt - 1] === " ")) {
      const fragment = val.slice(lastAt + 1);
      if (!fragment.includes(" ")) {
        setMentionFilter(fragment.toLowerCase());
        setShowMentions(true);
        return;
      }
    }
    setShowMentions(false);
  };

  const insertMention = (name: string) => {
    const lastAt = input.lastIndexOf("@");
    const before = input.slice(0, lastAt);
    setInput(`${before}@${name} `);
    setShowMentions(false);
    inputRef.current?.focus();
  };

  const loadSession = async (sid: string) => {
    try {
      const res = await fetch(`/api/v1/chat/history/${sid}`);
      const data = await res.json();
      setMessages(
        data.map((m: ChatMsg) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          created_at: m.created_at,
        }))
      );
      setSessionId(sid);
      setSidebarOpen(false);
    } catch {
      setError("Failed to load session");
    }
  };

  const startNewSession = () => {
    setSessionId("");
    setMessages([]);
    setError(null);
    setKnowledgeCount(null);
  };

  const filteredAgents = agents.filter((a) =>
    a.name.toLowerCase().includes(mentionFilter)
  );

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      {sidebarOpen && (
        <div className="w-56 shrink-0 border-r border-slate-700/40 flex flex-col bg-slate-900/40">
          <div className="p-3 flex items-center justify-between border-b border-slate-700/30">
            <span className="ui-label text-slate-400">sessions</span>
            <button
              onClick={() => setSidebarOpen(false)}
              className="text-slate-600 hover:text-slate-400 text-xs"
            >
              &times;
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {sessions.length === 0 && (
              <div className="p-3 text-[10px] text-slate-700">
                no sessions yet
              </div>
            )}
            {sessions.map((s) => (
              <button
                key={s.session_id}
                onClick={() => loadSession(s.session_id)}
                className={`w-full text-left px-3 py-2 border-b border-slate-800/40 hover:bg-slate-800/40 transition ${
                  s.session_id === sessionId
                    ? "bg-blue-600/10 border-l-2 border-l-blue-500"
                    : ""
                }`}
              >
                <div className="text-[10px] text-slate-400 truncate font-mono">
                  {s.session_id.slice(0, 12)}...
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[9px] text-slate-600">
                    {s.message_count} msgs
                  </span>
                  {s.last_message_at && (
                    <span className="text-[9px] text-slate-700">
                      {timeAgo(s.last_message_at)}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main chat */}
      <div className="flex-1 flex flex-col p-4 gap-3 min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-slate-600 hover:text-slate-400 transition text-sm"
              title="Toggle sessions"
            >
              &#9776;
            </button>
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

        {/* Project selector + context badge */}
        <div className="shrink-0 space-y-1">
          <select
            value={selectedProject}
            onChange={(e) => {
              setSelectedProject(e.target.value);
              setKnowledgeCount(null);
            }}
            className="w-full px-3 py-1.5 rounded-md bg-slate-800/60 border border-slate-700/40 text-xs text-slate-300 outline-none focus:border-blue-500/40 transition"
          >
            <option value="">no project context</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.slug})
              </option>
            ))}
          </select>
          {knowledgeCount !== null && knowledgeCount > 0 && (
            <div className="text-[9px] text-purple-400/70 px-1">
              {knowledgeCount} knowledge{" "}
              {knowledgeCount === 1 ? "entry" : "entries"}
            </div>
          )}
        </div>

        {/* Messages */}
        <div
          ref={scrollRef}
          className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-1"
        >
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-2">
                <div className="text-slate-700 text-2xl">&gt;_</div>
                <div className="ui-label text-slate-600">
                  start a conversation
                </div>
                <div className="text-[10px] text-slate-700 max-w-[280px]">
                  Ask questions about your projects, request code reviews, or
                  get implementation guidance. Use @agent to route to a specific
                  agent.
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
                <span
                  className="ui-label"
                  style={{
                    fontSize: 9,
                    color:
                      msg.role === "user" ? "#60a5fa" : "#a78bfa",
                  }}
                >
                  {msg.role === "user"
                    ? "you"
                    : msg.agent_name || "agent"}
                </span>
                <span className="text-slate-700" style={{ fontSize: 9 }}>
                  {new Date(msg.created_at).toLocaleTimeString()}
                </span>
              </div>
              {msg.role === "assistant" ? (
                <div className="chat-markdown">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                  >
                    {msg.content || " "}
                  </ReactMarkdown>
                </div>
              ) : (
                <div className="whitespace-pre-wrap">{msg.content}</div>
              )}
            </div>
          ))}

          {sending &&
            messages.length > 0 &&
            messages[messages.length - 1].content === "" && (
              <div className="fade-in flex items-center gap-2 px-3 py-2 text-xs text-slate-600">
                <span className="animate-pulse">...</span>
                <span className="ui-label" style={{ fontSize: 9 }}>
                  thinking
                </span>
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
        <div className="shrink-0 relative">
          {/* @mention dropdown */}
          {showMentions && filteredAgents.length > 0 && (
            <div className="absolute bottom-full mb-1 left-0 right-12 bg-slate-800 border border-slate-700/60 rounded-md shadow-lg z-10 max-h-32 overflow-y-auto">
              {filteredAgents.map((a) => (
                <button
                  key={a.id}
                  onClick={() => insertMention(a.name)}
                  className="w-full text-left px-3 py-1.5 hover:bg-slate-700/50 transition flex items-center gap-2"
                >
                  <span className="text-xs text-blue-400 font-mono">
                    @{a.name}
                  </span>
                  <span className="text-[9px] text-slate-600">{a.role}</span>
                </button>
              ))}
            </div>
          )}

          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              onBlur={() => setTimeout(() => setShowMentions(false), 150)}
              placeholder="ask something... (@agent to route)"
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
      </div>
    </div>
  );
}
