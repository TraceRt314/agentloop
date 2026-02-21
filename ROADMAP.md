# AgentLoop — Roadmap

## Vision

AgentLoop: plataforma multi-agente personal que corre en local (o en N servidores).
Dashboard accesible desde cualquier dispositivo de la red local.
Los agentes trabajan de verdad — con Claude Code, Ollama, OpenAI, o lo que quieras.
Les hablas desde la web, Telegram, WhatsApp, o por voz.
OpenClaw es el canal de comunicación y ejecución; AgentLoop es el cerebro orquestador.

### Arquitectura objetivo

```
Tú (Telegram / WhatsApp / Web UI / Voz)
    │
    ▼
OpenClaw Gateway (mensajería + ejecución LLM)
    │
    ▼
AgentLoop Central (orquestación, DB, dashboard)
    ├── Nodo local (OpenClaw + Claude Code)
    ├── Nodo servidor A (OpenClaw + Claude Code)
    └── Nodo servidor B (OpenClaw + Ollama)
```

---

## Fase 0 — Foundation ✅

> "Que cualquiera pueda hacer `git clone && make dev` y tener algo funcionando en 5 min"

- [x] 0.1 LLM provider agnóstico (OpenAI, Ollama, OpenRouter — plugin genérico)
- [x] 0.2 `.env.example` con Ollama como default
- [x] 0.3 Fix Docker (pnpm, standalone, ports)
- [x] 0.4 Makefile (`make dev`, `make seed`, `make test`, `make docker`)
- [x] 0.5 README.md (hero, quickstart, features, arquitectura)
- [x] 0.6 Limpiar dead code
- [x] 0.7 Fix bugs conocidos (TasksPanel ruta, EventFeed keys)
- [x] 0.8 URLs configurables (env vars para WS/API en frontend)

---

## Fase 1 — OpenClaw + Gestión de agentes ✅

> "Que configurar OpenClaw + Claude Code sea trivial, y que pueda añadir agentes eligiendo qué LLM usan"

- [x] 1.1 Setup guiado de OpenClaw — docs + script `make setup-openclaw` que configura el gateway, genera token, y conecta con AgentLoop
- [x] 1.2 UI de gestión de agentes — crear/editar agentes desde el dashboard: nombre, rol, LLM provider (Ollama/Claude/OpenAI/OpenRouter), modelo, nivel de reasoning (fast/balanced/deep), system prompt
- [x] 1.3 Modelo configurable por agente — cada agente puede usar un LLM distinto (ej: PM usa Claude Sonnet, dev usa Claude Code, QA usa Ollama local)
- [x] 1.4 Dashboard accesible en LAN — bind a `0.0.0.0`, mDNS/hostname, accesible desde móvil/tablet en la misma red
- [x] 1.5 Health checks visuales — ver en el dashboard qué nodos están conectados, qué LLMs responden, latencia

---

## Fase 2 — Chat de verdad ✅

> "Que hablar con tus agentes desde la web sea fluido — streaming, markdown, contexto"

- [x] 2.1 Streaming responses (SSE) — el chat muestra tokens en tiempo real conforme el LLM responde
- [x] 2.2 Markdown + syntax highlighting en respuestas (code blocks, listas, tablas)
- [x] 2.3 Historial persistente — el chat sobrevive a reloads, con sesiones navegables
- [x] 2.4 Contexto de proyecto inyectado — el agente sabe en qué proyecto trabaja, qué archivos hay, qué se hizo antes
- [x] 2.5 Multi-agente en chat — hablar con agentes específicos (`@dev haz X`, `@pm prioriza Y`). OpenClaw ya soporta multi-agent routing; AgentLoop debe exponerlo en la UI

---

## Fase 3 — Canales de mensajería (via OpenClaw)

> "Háblale a tus agentes desde Telegram, WhatsApp, o Discord — OpenClaw ya lo hace, solo hay que conectarlo"

- [ ] 3.1 Guía de setup Telegram — paso a paso: crear bot con @BotFather, configurar en `openclaw.json`, bindings a agentes de AgentLoop
- [ ] 3.2 Bidireccional Telegram ↔ AgentLoop — mensajes de Telegram llegan a AgentLoop como tareas/chat; respuestas de agentes se envían de vuelta por Telegram
- [ ] 3.3 Notificaciones — misión completada, step fallido, propuesta pendiente → se notifica por Telegram/WhatsApp
- [ ] 3.4 Guía de setup WhatsApp/Discord — mismo patrón que Telegram, usando canales nativos de OpenClaw
- [ ] 3.5 Comandos desde mensajería — `/status`, `/agents`, `/task <título>` mapeados a la API de AgentLoop

---

## Fase 4 — Multi-servidor

> "Que pueda tener AgentLoop + OpenClaw + Claude Code en N servidores, con un backend central donde se persisten los datos"

- [ ] 4.1 Backend central con PostgreSQL — migrar de SQLite a Postgres para el nodo central (SQLite sigue como opción local)
- [ ] 4.2 Registro de nodos — API para registrar servidores worker. Cada nodo tiene: URL, OpenClaw gateway, LLMs disponibles, capacidad
- [ ] 4.3 Dispatch inteligente — el orchestrator elige qué nodo ejecuta cada step según: LLM requerido, carga actual, proyecto, capabilities
- [ ] 4.4 UI de servidores — panel en el dashboard para ver/añadir/quitar nodos, su estado, qué agentes corren en cada uno
- [ ] 4.5 Remote access — setup con Tailscale/SSH para acceder a nodos remotos de forma segura (OpenClaw ya soporta esto)
- [ ] 4.6 Sincronización de estado — los nodos worker reportan resultados al central; el central persiste todo

---

## Fase 5 — Voz

> "Habla con tus agentes — desde la web o desde Telegram"

- [ ] 5.1 Voice notes via Telegram/WhatsApp — OpenClaw ya transcribe voice notes; AgentLoop procesa el texto y responde
- [ ] 5.2 STT en frontend (Web Speech API) — botón de micrófono en el chat web
- [ ] 5.3 TTS en frontend (Web Speech API) — las respuestas se leen en voz alta
- [ ] 5.4 Modo manos libres — activación por voz, conversación continua
- [ ] 5.5 Opcional: ElevenLabs/OpenAI TTS para voces más naturales

---

## Fase 6 — Productividad real

> "Que los agentes hagan cosas útiles de verdad"

- [ ] 6.1 Tool use / function calling — los agentes pueden ejecutar herramientas (shell, API calls, file ops) via Claude Code
- [ ] 6.2 Workspace personal — notas, docs, knowledge base accesible desde cualquier canal
- [ ] 6.3 Scheduling — reminders, tareas programadas, cron jobs via OpenClaw
- [ ] 6.4 Integraciones — GitHub (PRs, issues), Calendar, Email
- [ ] 6.5 RAG local — embeddings con Ollama para buscar en documentos propios

---

## Fase 7 — Conversación en tiempo real (Web)

> "Que desde el navegador pueda tener una conversación fluida, como hablar con un compañero"

- [ ] 7.1 WebRTC o WebSocket bidireccional para audio — hablar desde el browser sin latencia
- [ ] 7.2 Interrupciones naturales — poder cortar al agente mientras habla
- [ ] 7.3 Contexto visual — el agente en la oficina isométrica muestra que está "escuchando" o "hablando"
- [ ] 7.4 Multi-turno fluido — conversación continua sin pulsar botones

---

## Fase 8 — Polish para lanzamiento

> "Que se vea profesional y confiable"

- [ ] 8.1 Auth básica (API key / sesión local)
- [ ] 8.2 Onboarding wizard — guía interactiva que configura LLM, crea agentes, conecta OpenClaw
- [ ] 8.3 Landing page
- [ ] 8.4 CI/CD (GitHub Actions)
- [ ] 8.5 CONTRIBUTING.md + issue templates
- [ ] 8.6 Demo GIF / video (30s)
- [ ] 8.7 LICENSE (MIT)
