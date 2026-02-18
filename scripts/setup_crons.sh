#!/bin/bash

# AgentLoop OpenClaw Integration Setup Script
# This script sets up cron jobs in OpenClaw for AgentLoop orchestration

set -e

# Configuration
API_BASE_URL="${AGENTLOOP_API_BASE_URL:-http://localhost:8000}"
ORCHESTRATOR_SCHEDULE="${AGENTLOOP_ORCHESTRATOR_SCHEDULE:-*/5 * * * *}"  # Every 5 minutes
AGENTS_SCHEDULE="${AGENTLOOP_AGENTS_SCHEDULE:-*/10 * * * *}"             # Every 10 minutes

echo "AgentLoop OpenClaw Integration Setup"
echo "===================================="
echo ""
echo "API Base URL: $API_BASE_URL"
echo "Orchestrator Schedule: $ORCHESTRATOR_SCHEDULE"
echo "Agents Schedule: $AGENTS_SCHEDULE"
echo ""

# Check if OpenClaw CLI is available
if ! command -v openclaw &> /dev/null; then
    echo "Error: OpenClaw CLI not found"
    echo "Please install OpenClaw CLI first"
    exit 1
fi

# Check if AgentLoop API is running
echo "Checking if AgentLoop API is running..."
if ! curl -s "$API_BASE_URL/healthz" > /dev/null 2>&1; then
    echo "Warning: AgentLoop API is not responding at $API_BASE_URL"
    echo "Please make sure the AgentLoop server is running before setting up cron jobs"
    echo ""
fi

# Set up orchestrator cron job
echo "Setting up orchestrator cron job..."
ORCHESTRATOR_COMMAND="curl -s -X POST $API_BASE_URL/api/v1/orchestrator/tick"
openclaw cron add "$ORCHESTRATOR_SCHEDULE" "$ORCHESTRATOR_COMMAND" \
    --description "AgentLoop orchestrator tick - runs closed-loop orchestration cycle"

echo "✓ Orchestrator cron job created"

# Function to set up agent work cycle cron jobs
setup_agent_cron() {
    local agent_id="$1"
    local agent_name="$2"
    
    if [ -z "$agent_id" ]; then
        echo "Error: Agent ID is required"
        return 1
    fi
    
    local command="curl -s -X POST $API_BASE_URL/api/v1/orchestrator/work-cycle/$agent_id"
    local description="AgentLoop agent work cycle for $agent_name (ID: $agent_id)"
    
    openclaw cron add "$AGENTS_SCHEDULE" "$command" --description "$description"
    echo "✓ Agent work cycle cron job created for $agent_name ($agent_id)"
}

# Get list of agents from AgentLoop API and set up their cron jobs
echo ""
echo "Setting up agent work cycle cron jobs..."

if curl -s "$API_BASE_URL/healthz" > /dev/null 2>&1; then
    # API is running, fetch agents
    AGENTS_JSON=$(curl -s "$API_BASE_URL/api/v1/agents" || echo "[]")
    
    if [ "$AGENTS_JSON" != "[]" ] && [ "$AGENTS_JSON" != "" ]; then
        # Parse JSON and set up cron jobs for each agent
        # Note: This requires jq for JSON parsing
        if command -v jq &> /dev/null; then
            echo "$AGENTS_JSON" | jq -r '.[] | "\(.id) \(.name) \(.role)"' | while read -r agent_id agent_name agent_role; do
                setup_agent_cron "$agent_id" "$agent_name ($agent_role)"
            done
        else
            echo "Warning: jq not found - cannot automatically set up agent cron jobs"
            echo "Please install jq or manually set up agent work cycle cron jobs:"
            echo ""
            echo "For each agent, run:"
            echo "  openclaw cron add \"$AGENTS_SCHEDULE\" \"curl -s -X POST $API_BASE_URL/api/v1/orchestrator/work-cycle/AGENT_ID\" --description \"AgentLoop agent work cycle for AGENT_NAME\""
        fi
    else
        echo "No agents found in AgentLoop"
        echo "You can manually add agent work cycle cron jobs later using:"
        echo "  openclaw cron add \"$AGENTS_SCHEDULE\" \"curl -s -X POST $API_BASE_URL/api/v1/orchestrator/work-cycle/AGENT_ID\" --description \"AgentLoop agent work cycle for AGENT_NAME\""
    fi
else
    echo "AgentLoop API not available - skipping automatic agent cron setup"
    echo ""
    echo "After starting AgentLoop, you can set up agent cron jobs manually:"
    echo "1. Get agent IDs: curl $API_BASE_URL/api/v1/agents"
    echo "2. For each agent, run:"
    echo "   openclaw cron add \"$AGENTS_SCHEDULE\" \"curl -s -X POST $API_BASE_URL/api/v1/orchestrator/work-cycle/AGENT_ID\" --description \"AgentLoop agent work cycle\""
fi

echo ""
echo "Cron jobs setup complete!"
echo ""
echo "You can:"
echo "- List cron jobs: openclaw cron list"
echo "- View cron logs: openclaw cron logs JOB_ID"
echo "- Remove cron jobs: openclaw cron remove JOB_ID"
echo ""
echo "AgentLoop closed-loop orchestration is now active!"
echo ""
echo "Monitor the system:"
echo "- API health: curl $API_BASE_URL/healthz"
echo "- Orchestrator status: curl $API_BASE_URL/api/v1/orchestrator/status"
echo "- Recent events: curl $API_BASE_URL/api/v1/events"
echo ""

# Make the script executable
chmod +x "$0"