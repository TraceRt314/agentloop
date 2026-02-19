# AgentLoop

**Multi-agent orchestration platform with a visual office interface.**

AgentLoop lets you define autonomous AI agents that collaborate on projects — claiming tasks, writing code, reviewing work, and deploying changes — all visible in a real-time isometric virtual office.

## Architecture

```
┌──────────────────────────────────────────────────┐
│                   Frontend (Next.js)             │
│    Isometric Office  │  Tasks Panel  │  System   │
│    PixiJS WebGL      │  MC Boards    │  Health   │
└──────────┬───────────┴──────┬────────┴───────────┘
           │ WebSocket        │ REST
┌──────────▼──────────────────▼────────────────────┐
│              AgentLoop API (FastAPI)              │
│   Agents  │  Missions  │  Steps  │  Simulation   │
└─────┬─────┴─────┬──────┴────┬────┴───────────────┘
      │           │           │
      ▼           ▼           ▼
  OpenClaw    Mission      SQLite
  Gateway     Control       DB
  (agent      (governance,
   execution)  boards)
```

### Components

- **AgentLoop API** — FastAPI backend. Manages agents, missions, steps, proposals, and the simulation tick.
- **Frontend** — Next.js + PixiJS. Real-time isometric office where you can watch agents move, work, and collaborate.
- **OpenClaw Gateway** — Routes work to AI agents via the `openclaw agent` CLI. Agents execute tasks and return results.
- **Mission Control** — Governance layer. Boards, tasks, approvals, and audit trails.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- [OpenClaw](https://openclaw.ai) installed (`npm i -g openclaw`)
- [Mission Control](https://github.com/openclaw/mission-control) running (optional, for task governance)

### Backend

```bash
git clone https://github.com/YOUR_USERNAME/agentloop.git
cd agentloop

# Create virtualenv and install
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your tokens

# Seed the database
python scripts/seed.py --name "My Project" --slug my-project --repo /path/to/repo

# Run
uvicorn agentloop.main:app --host 127.0.0.1 --port 8080 --reload
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Open http://localhost:3002 to see the office.

### Daemon mode (macOS)

Run AgentLoop as a background service using LaunchAgents:

```bash
./scripts/install-launchd.sh install    # start on login
./scripts/install-launchd.sh uninstall  # stop and remove
```

This installs two LaunchAgents:
- **`com.agentloop.server`** — uvicorn backend on port 8080
- **`com.agentloop.ticker`** — periodic simulation, orchestrator, and MC sync ticks

Logs are written to `~/Library/Logs/AgentLoop/`.

### Docker

```bash
docker compose up
```

## Configuration

All settings are controlled via environment variables (prefix `AGENTLOOP_`). See [`.env.example`](.env.example) for the full list.

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENTLOOP_DATABASE_URL` | SQLite or PostgreSQL connection string | `sqlite:///./agentloop.db` |
| `AGENTLOOP_OPENCLAW_GATEWAY_URL` | OpenClaw gateway WebSocket URL | `ws://localhost:18789` |
| `AGENTLOOP_MC_BASE_URL` | Mission Control API URL | `http://localhost:8002` |
| `AGENTLOOP_MC_TOKEN` | Mission Control auth token | — |
| `AGENTLOOP_MC_ORG_ID` | Mission Control organization ID | — |
| `AGENTLOOP_BOARD_MAP` | JSON mapping of MC board UUIDs to project slugs | `{}` |
| `AGENTLOOP_STEP_TIMEOUT_SECONDS` | Max time for agent to complete a step | `300` |

## How It Works

1. **Projects** have **agents** with roles (PM, developer, QA, deployer).
2. Tasks from Mission Control become **proposals** that get approved into **missions**, then broken into **steps**.
3. The **worker engine** claims steps and dispatches them to the OpenClaw agent via CLI.
4. The agent executes the work (code, tests, reviews) and returns results.
5. **Triggers** chain steps automatically (e.g., dev complete → QA review → deploy).
6. The **simulation tick** moves agent avatars around the virtual office in real time.

## Project Structure

```
agentloop/
├── agentloop/             # Python backend
│   ├── api/               # FastAPI routes
│   ├── engine/            # Worker engine, movement, orchestrator
│   ├── integrations/      # OpenClaw, Mission Control clients
│   ├── models.py          # SQLModel schemas
│   └── config.py          # Pydantic settings
├── frontend/              # Next.js + PixiJS UI
│   ├── app/               # Pages and layout
│   ├── components/        # React components
│   └── lib/               # Types, WebSocket hook
├── agents/                # Agent role configs (YAML)
├── projects/              # Project configs (YAML)
├── scripts/               # Seed script
└── docker-compose.yml
```

## API

Once running, interactive docs at: http://localhost:8080/docs

Key endpoints:

- `GET /api/v1/dashboard/overview` — Full platform overview
- `POST /api/v1/simulation/tick` — Run one simulation tick
- `POST /api/v1/simulation/demo` — Trigger demo activity
- `GET /api/v1/agents` — List all agents
- `GET /api/v1/missions` — List missions
- `POST /api/v1/proposals` — Create a new proposal

## License

MIT — see [LICENSE](LICENSE).
