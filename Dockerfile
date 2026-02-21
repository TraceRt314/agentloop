# ─── Stage 1: Build ───
FROM python:3.12-slim AS builder

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY . .

# ─── Stage 2: Runtime ───
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY agentloop /app/agentloop
COPY plugins /app/plugins
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY scripts /app/scripts

RUN mkdir -p /app/agents /app/projects /app/data

ENV AGENTLOOP_DATABASE_URL="sqlite:///./data/agentloop.db"
ENV AGENTLOOP_API_HOST="0.0.0.0"
ENV AGENTLOOP_API_PORT="8080"
ENV AGENTLOOP_DEBUG="false"
ENV AGENTLOOP_ENABLED_PLUGINS="llm,knowledge,office-viz,tasks"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:8080/healthz || exit 1

CMD ["uvicorn", "agentloop.main:app", "--host", "0.0.0.0", "--port", "8080"]
