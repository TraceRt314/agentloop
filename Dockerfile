# ─── Stage 1: Build ───
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev


# ─── Stage 2: Runtime ───
FROM python:3.12-slim

WORKDIR /app

# curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/agentloop /app/agentloop
COPY --from=builder /app/alembic.ini /app/alembic.ini
COPY --from=builder /app/migrations /app/migrations

# Default dirs for agent/project YAML configs
RUN mkdir -p /app/agents /app/projects /app/data

ENV PATH="/app/.venv/bin:$PATH"
ENV AGENTLOOP_DATABASE_URL="sqlite:///./data/agentloop.db"
ENV AGENTLOOP_API_HOST="0.0.0.0"
ENV AGENTLOOP_API_PORT="8000"
ENV AGENTLOOP_DEBUG="false"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "agentloop.main:app", "--host", "0.0.0.0", "--port", "8000"]
