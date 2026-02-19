#!/bin/bash
# AgentLoop daemon ticker — calls simulation, orchestrator, and MC sync
# Usage: ./ticker.sh [interval_seconds]

API="${AGENTLOOP_API_BASE_URL:-http://localhost:8080}"
INTERVAL=${1:-15}
TICK_COUNT=0
SYNC_EVERY=20  # MC sync every N ticks (~5 min at 15s interval)
ORCH_EVERY=4   # Orchestrator tick every N ticks (~1 min at 15s interval)
HEALTH_EVERY=10 # Health check every N ticks (~2.5 min at 15s interval)

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "AgentLoop ticker started (interval: ${INTERVAL}s)"
log "API: $API"

while true; do
  TICK_COUNT=$((TICK_COUNT + 1))

  # Simulation tick (every tick — animation)
  curl -s -X POST "$API/api/v1/simulation/tick" > /dev/null 2>&1

  # Demo activity (every 3rd tick — idle agent movement)
  if [ $((TICK_COUNT % 3)) -eq 0 ]; then
    curl -s -X POST "$API/api/v1/simulation/demo" > /dev/null 2>&1
  fi

  # Orchestrator tick (every ORCH_EVERY ticks — process proposals/missions/steps)
  if [ $((TICK_COUNT % ORCH_EVERY)) -eq 0 ]; then
    curl -s -X POST "$API/api/v1/orchestrator/tick" > /dev/null 2>&1
  fi

  # MC sync (every SYNC_EVERY ticks — pull tasks, report completions)
  if [ $((TICK_COUNT % SYNC_EVERY)) -eq 0 ]; then
    curl -s -X POST "$API/api/v1/simulation/sync-mc" > /dev/null 2>&1
  fi

  # Health check (every HEALTH_EVERY ticks — log warnings)
  if [ $((TICK_COUNT % HEALTH_EVERY)) -eq 0 ]; then
    HEALTH=$(curl -s "$API/api/v1/health" 2>/dev/null)
    STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null)
    if [ "$STATUS" != "healthy" ]; then
      log "HEALTH: $STATUS"
      echo "$HEALTH" | python3 -m json.tool >&2
    fi
  fi

  sleep "$INTERVAL"
done
