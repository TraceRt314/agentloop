#!/usr/bin/env bash
# setup-openclaw.sh — Install and configure OpenClaw gateway for AgentLoop
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[ok]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!!]${NC} $1"; }
fail()  { echo -e "${RED}[error]${NC} $1"; exit 1; }

echo ""
echo "  OpenClaw Setup for AgentLoop"
echo "  ────────────────────────────"
echo ""

# 1. Check if openclaw CLI is in PATH
if command -v openclaw &>/dev/null; then
  info "openclaw found: $(command -v openclaw)"
else
  warn "openclaw not found in PATH"
  echo "  Installing openclaw globally via npm..."
  npm i -g openclaw || fail "Failed to install openclaw. Check npm permissions."
  info "openclaw installed: $(command -v openclaw)"
fi

# 2. Run onboarding if no config exists
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
if [ -f "$OPENCLAW_CONFIG" ]; then
  info "openclaw config found: $OPENCLAW_CONFIG"
else
  warn "No openclaw config found — running onboarding"
  openclaw onboard || fail "Onboarding failed"
  [ -f "$OPENCLAW_CONFIG" ] || fail "Config file not created after onboarding"
  info "onboarding complete"
fi

# 3. Extract gateway token from config
TOKEN=""
if command -v python3 &>/dev/null; then
  TOKEN=$(python3 -c "
import json, sys
try:
    with open('$OPENCLAW_CONFIG') as f:
        cfg = json.load(f)
    token = cfg.get('gateway', {}).get('token', '') or cfg.get('token', '')
    print(token)
except Exception as e:
    print('', file=sys.stderr)
" 2>/dev/null || true)
fi

if [ -z "$TOKEN" ]; then
  warn "Could not extract gateway token automatically"
  echo "  Please add AGENTLOOP_OPENCLAW_GATEWAY_TOKEN manually to .env"
else
  info "gateway token extracted"
fi

# 4. Write token to .env if present
ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"
if [ -n "$TOKEN" ] && [ -f "$ENV_FILE" ]; then
  if grep -q "^AGENTLOOP_OPENCLAW_GATEWAY_TOKEN=" "$ENV_FILE" 2>/dev/null; then
    # Update existing line
    sed -i.bak "s|^AGENTLOOP_OPENCLAW_GATEWAY_TOKEN=.*|AGENTLOOP_OPENCLAW_GATEWAY_TOKEN=$TOKEN|" "$ENV_FILE"
    rm -f "${ENV_FILE}.bak"
  else
    echo "" >> "$ENV_FILE"
    echo "AGENTLOOP_OPENCLAW_GATEWAY_TOKEN=$TOKEN" >> "$ENV_FILE"
  fi
  info "token written to .env"
elif [ -n "$TOKEN" ]; then
  warn ".env file not found — run 'cp .env.example .env' first"
fi

# 5. Ensure openclaw plugin is enabled
if [ -f "$ENV_FILE" ]; then
  PLUGINS=$(grep "^AGENTLOOP_ENABLED_PLUGINS=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 || true)
  if [ -n "$PLUGINS" ] && ! echo "$PLUGINS" | grep -q "openclaw"; then
    NEW_PLUGINS="${PLUGINS},openclaw"
    sed -i.bak "s|^AGENTLOOP_ENABLED_PLUGINS=.*|AGENTLOOP_ENABLED_PLUGINS=$NEW_PLUGINS|" "$ENV_FILE"
    rm -f "${ENV_FILE}.bak"
    info "added openclaw to enabled plugins"
  fi
fi

# 6. Health check
echo ""
echo "  Running health check..."
if openclaw agent --session-id "setup-test" --message "PING" --json 2>/dev/null | grep -q "status"; then
  info "openclaw gateway responding"
else
  warn "gateway health check failed — is the gateway running?"
  echo "  Start it with: openclaw gateway start"
fi

echo ""
info "setup complete"
echo ""
echo "  Next steps:"
echo "    1. Ensure the gateway is running: openclaw gateway start"
echo "    2. Enable the openclaw plugin in .env:"
echo "       AGENTLOOP_ENABLED_PLUGINS=llm,knowledge,office-viz,tasks,openclaw"
echo "    3. Create agents with provider=openclaw in the Agents tab"
echo ""
