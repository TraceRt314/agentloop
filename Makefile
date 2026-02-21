.PHONY: install dev backend frontend seed test lint docker clean help

PYTHON := .venv/bin/python
UVICORN := .venv/bin/uvicorn

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────

install: ## Install all dependencies (backend + frontend)
	@echo "── backend ──"
	python3 -m venv .venv 2>/dev/null || true
	$(PYTHON) -m pip install -e ".[dev]" --quiet
	@echo "── frontend ──"
	cd frontend && pnpm install --frozen-lockfile
	@echo "── done ──"
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")

# ── Development ──────────────────────────────────────────────

dev: ## Start backend + frontend (parallel)
	@make -j2 backend frontend

backend: ## Start FastAPI backend (port 8080)
	$(UVICORN) agentloop.main:app --host 127.0.0.1 --port 8080 --reload

frontend: ## Start Next.js frontend (port 3002)
	cd frontend && pnpm dev

# ── Data ─────────────────────────────────────────────────────

seed: ## Seed database with example project + agents
	$(PYTHON) scripts/seed.py

# ── Quality ──────────────────────────────────────────────────

test: ## Run backend tests
	$(PYTHON) -m pytest tests/ -v

lint: ## Run linters (black + isort check)
	$(PYTHON) -m black --check agentloop/ plugins/
	$(PYTHON) -m isort --check agentloop/ plugins/

format: ## Auto-format code
	$(PYTHON) -m black agentloop/ plugins/
	$(PYTHON) -m isort agentloop/ plugins/

# ── Docker ───────────────────────────────────────────────────

docker: ## Build and run with Docker Compose
	docker compose up --build

docker-build: ## Build Docker images only
	docker compose build

# ── Cleanup ──────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	rm -rf .venv __pycache__ .pytest_cache
	rm -rf frontend/.next frontend/node_modules
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
