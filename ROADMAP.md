# AgentLoop — Roadmap to Open-Source Launch

## Vision

AgentLoop: un asistente multi-agente personal que cualquiera puede correr en local.
Interactúa via web UI (con oficina isométrica), Telegram, y voz.
Open-source, zero dependencias propietarias, funciona con Ollama out-of-the-box.

---

## Fase 0 — Foundation

> "Que cualquiera pueda hacer `git clone && make dev` y tener algo funcionando en 5 min"

- [x] 0.1 LLM provider agnóstico (OpenAI, Anthropic, Ollama, OpenRouter — sin OpenClaw)
- [x] 0.2 `.env.example` con Ollama como default
- [x] 0.3 Fix Docker (pnpm, standalone, ports)
- [x] 0.4 Makefile (`make dev`, `make seed`, `make test`, `make docker`)
- [x] 0.5 README.md (hero, quickstart, features, arquitectura)
- [x] 0.6 Limpiar dead code
- [x] 0.7 Fix bugs conocidos (TasksPanel ruta, EventFeed keys)
- [x] 0.8 URLs configurables (env vars para WS/API en frontend)

## Fase 1 — Chat de verdad

> "Que hablar con tus agentes sea una experiencia fluida"

- [ ] 1.1 Streaming responses (SSE)
- [ ] 1.2 Markdown + syntax highlighting
- [ ] 1.3 Historial persistente entre reloads
- [ ] 1.4 Contexto de proyecto inyectado
- [ ] 1.5 Multi-agente en chat (`@dev`, `@pm`)

## Fase 2 — Telegram bot

> "Háblale a tus agentes desde el móvil"

- [ ] 2.1 Plugin `telegram` (python-telegram-bot)
- [ ] 2.2 Comandos: `/ask`, `/status`, `/task`, `/agents`
- [ ] 2.3 Forward de respuestas bidireccional
- [ ] 2.4 Notificaciones (misión completada, step fallido)
- [ ] 2.5 Configuración guiada en README

## Fase 3 — Voz

> "Habla con tus agentes como si fueran compañeros"

- [ ] 3.1 STT en frontend (Web Speech API)
- [ ] 3.2 TTS en frontend (Web Speech API)
- [ ] 3.3 Modo manos libres
- [ ] 3.4 Voz por Telegram (voice messages → STT)
- [ ] 3.5 Opcional: ElevenLabs/OpenAI TTS

## Fase 4 — Productividad real

> "Que los agentes hagan cosas útiles de verdad"

- [ ] 4.1 Tool use / function calling
- [ ] 4.2 Plantillas de proyecto
- [ ] 4.3 Workspace personal (notas, docs, KB)
- [ ] 4.4 Scheduling (reminders, cron)
- [ ] 4.5 Integraciones (GitHub, Calendar, Email)
- [ ] 4.6 RAG local (embeddings con Ollama)

## Fase 5 — Polish para lanzamiento

> "Que se vea profesional y confiable"

- [ ] 5.1 Auth básica (API key / sesión local)
- [ ] 5.2 Onboarding wizard
- [ ] 5.3 Landing page
- [ ] 5.4 CI/CD (GitHub Actions)
- [ ] 5.5 CONTRIBUTING.md + issue templates
- [ ] 5.6 Demo GIF / video (30s)
- [ ] 5.7 LICENSE (MIT)
