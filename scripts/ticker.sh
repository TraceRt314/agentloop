#!/bin/bash
# AgentLoop simulation ticker — runs in background
# Calls simulation/tick + simulation/demo every N seconds

API="http://localhost:8080"
INTERVAL=${1:-15}  # Default: 15 seconds

echo "🔄 AgentLoop ticker started (interval: ${INTERVAL}s)"
echo "   API: $API"
echo "   Press Ctrl+C to stop"

while true; do
  curl -s -X POST "$API/api/v1/simulation/tick" > /dev/null 2>&1
  # Demo activity less frequently (every 3rd tick)
  if [ $((RANDOM % 3)) -eq 0 ]; then
    curl -s -X POST "$API/api/v1/simulation/demo" > /dev/null 2>&1
  fi
  sleep "$INTERVAL"
done
