<h1 align="center">AgentLoop</h1>

<p align="center">
  <strong>Your personal multi-agent AI team, running locally.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue?style=flat-square" alt="Python 3.12+" />
  <img src="https://img.shields.io/badge/node-20+-green?style=flat-square" alt="Node 20+" />
  <img src="https://img.shields.io/badge/LLM-Ollama%20%7C%20OpenAI%20%7C%20OpenRouter-purple?style=flat-square" alt="LLM Support" />
  <img src="https://img.shields.io/badge/license-MIT-gray?style=flat-square" alt="MIT License" />
</p>

<p align="center">
  <em>Define AI agents with roles — PM, developer, QA, deployer — and watch them collaborate<br/>
  in a real-time isometric virtual office. Works with Ollama out of the box. No API keys needed.</em>
</p>

---

## What is AgentLoop?

AgentLoop is a **local-first, open-source multi-agent platform**. You define a team of AI agents, each with a role and capabilities, and they work together on projects: reviewing tasks, writing code, running tests, and deploying changes.

Everything happens in a **real-time isometric office** where you can see your agents walking around, working at their desks, and collaborating — like a tiny AI company running on your laptop.

### Key features

- **Works with Ollama** — No API keys, no cloud. Run `ollama pull llama3.2` and you're set.
- **Pluggable LLM** — Switch to OpenAI, OpenRouter, or any OpenAI-compatible API with one env var.
- **Visual office** — PixiJS-powered isometric office with day/night cycle, animated agents, and particle effects.
- **Plugin system** — Everything is a plugin: LLM backends, task management, knowledge base, visualizations.
- **Chat interface** — Talk to your agents directly from the web UI.
- **Task orchestration** — Proposals → missions → steps. Agents claim work, execute it, and chain results.
- **Knowledge base** — Per-project memory that agents learn from over time.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+ with pnpm
- [Ollama](https://ollama.ai) (recommended) or any OpenAI-compatible API

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/agentloop.git
cd agentloop
make install
```

### 2. Pull a model

```bash
ollama pull llama3.2
```

### 3. Seed and run

```bash
make seed    # creates example project + 5 agents
make dev     # starts backend (8080) + frontend (3002)
```

Open **http://localhost:3002** — you'll see the office with your agents.

### Docker alternative

```bash
cp .env.example .env
docker compose up
```

## Architecture

```
┌─────────────────────────────────────────────┐
│              Frontend (Next.js)             │
│  ┌──────────┬─────────┬────────┬──────────┐ │
│  │  Office  │  Tasks  │  Chat  │  System  │ │
│  └────┬─────┴────┬────┴───┬────┴────┬─────┘ │
│       │ WebSocket │  REST  │  REST   │       │
└───────┼──────────┼────────┼─────────┼───────┘
        │          │        │         │
┌───────┴──────────┴────────┴─────────┴───────┐
│           AgentLoop API (FastAPI)           │
│  ┌──────────┬───────────┬────────────────┐  │
│  │  Core    │  Worker   │  Plugin Mgr    │  │
│  │  Engine  │  Engine   │  (discovers    │  │
│  │          │           │   plugins/)    │  │
│  └────┬─────┴─────┬─────┴───────┬────────┘  │
│       │           │             │            │
│  ┌────┴────┐ ┌────┴────┐  ┌────┴─────────┐  │
│  │ SQLite  │ │   LLM   │  │  Plugins:    │  │
│  │   DB    │ │ (Ollama/ │  │  knowledge,  │  │
│  │         │ │  OpenAI) │  │  tasks, ...  │  │
│  └─────────┘ └─────────┘  └──────────────┘  │
└─────────────────────────────────────────────┘
```

## How It Works

1. **Projects** have **agents** with roles (PM, developer, QA, deployer, security).
2. You create **proposals** (tasks) → they become **missions** → broken into **steps**.
3. The **worker engine** claims steps and sends them to the LLM (Ollama by default).
4. Agents execute work (code, tests, reviews) and return results.
5. **Triggers** chain steps automatically (dev complete → QA review → deploy).
6. The **simulation** moves agent avatars around the virtual office in real time.

## Configuration

All settings use the `AGENTLOOP_` prefix. Copy `.env.example` to `.env` and adjust:

```bash
# LLM — default: Ollama (no API key needed)
AGENTLOOP_LLM_PROVIDER=ollama
AGENTLOOP_LLM_MODEL=llama3.2
AGENTLOOP_LLM_BASE_URL=http://localhost:11434/v1
AGENTLOOP_LLM_API_KEY=

# To use OpenAI instead:
# AGENTLOOP_LLM_PROVIDER=openai
# AGENTLOOP_LLM_MODEL=gpt-4o-mini
# AGENTLOOP_LLM_API_KEY=sk-...

# To use OpenRouter:
# AGENTLOOP_LLM_PROVIDER=openrouter
# AGENTLOOP_LLM_MODEL=anthropic/claude-sonnet-4-6
# AGENTLOOP_LLM_API_KEY=sk-or-...
```

See [`.env.example`](.env.example) for the full list of options.

## Plugin System

AgentLoop uses a directory-based plugin system. Each plugin is a folder in `plugins/` with a `plugin.yaml` manifest.

### Built-in Plugins

| Plugin | Description |
|--------|-------------|
| `llm` | Generic LLM provider — Ollama, OpenAI, OpenRouter support |
| `knowledge` | Knowledge base — global KB, documents, auto-learning |
| `office-viz` | Isometric office simulation — agent movement |
| `tasks` | Task management — comments, labels, templates |

### Creating a Plugin

```yaml
# plugins/my-plugin/plugin.yaml
name: my-plugin
version: "0.1.0"
description: What this plugin does
hooks:
  - hooks     # Python module with HOOKS dict
routes:
  - routes    # Python module with FastAPI router
```

```python
# plugins/my-plugin/hooks.py
def on_startup(**kwargs):
    print("My plugin loaded!")

HOOKS = {"on_startup": on_startup}
```

### Available Hooks

| Hook | When | Kwargs |
|------|------|--------|
| `on_startup` | App starts | `app` |
| `on_shutdown` | App stops | `app` |
| `on_step_complete` | Step finishes | `session`, `step`, `agent` |
| `on_mission_complete` | Mission done | `session`, `mission` |
| `on_tick` | Orchestration tick | `session` |

## Project Structure

```
agentloop/
├── agentloop/             # Python backend
│   ├── api/               # FastAPI routes
│   ├── engine/            # Orchestrator + worker
│   ├── models.py          # SQLModel schemas
│   ├── plugin.py          # Plugin manager
│   └── config.py          # Settings
├── plugins/               # Plugins
│   ├── llm/               # LLM provider (Ollama/OpenAI)
│   ├── knowledge/         # Knowledge base
│   ├── office-viz/        # Office simulation
│   └── tasks/             # Task management
├── frontend/              # Next.js UI
│   ├── components/        # React components
│   └── lib/               # Types, WebSocket
├── agents/                # Agent role configs (YAML)
├── projects/              # Project configs (YAML)
├── scripts/               # Seed, setup scripts
├── Makefile               # Dev commands
└── docker-compose.yml
```

## API

Interactive docs at: http://localhost:8080/docs

| Endpoint | Description |
|----------|-------------|
| `GET /healthz` | Health check |
| `POST /api/v1/orchestrator/tick` | Run orchestration cycle |
| `POST /api/v1/chat/` | Chat with agents |
| `GET /api/v1/agents` | List agents |
| `GET /api/v1/plugins` | List plugins |

## Contributing

1. Fork the repo
2. `make install`
3. Create a feature branch
4. `make test`
5. Submit a PR

## License

MIT
