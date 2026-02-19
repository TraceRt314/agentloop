#!/bin/bash
# Install or uninstall AgentLoop LaunchAgents (macOS)
# Usage:
#   ./scripts/install-launchd.sh install   — install and start
#   ./scripts/install-launchd.sh uninstall — stop and remove

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
LOGS_DIR="$HOME/Library/Logs/AgentLoop"
PLIST_DIR="$HOME/Library/LaunchAgents"
TEMPLATE_DIR="$PROJECT_DIR/scripts/launchd"

SERVER_LABEL="com.agentloop.server"
TICKER_LABEL="com.agentloop.ticker"

install() {
    echo "Installing AgentLoop LaunchAgents..."
    echo "  Project: $PROJECT_DIR"
    echo "  Venv:    $VENV_DIR"
    echo "  Logs:    $LOGS_DIR"
    echo ""

    # Verify venv exists
    if [ ! -f "$VENV_DIR/bin/uvicorn" ]; then
        echo "Error: virtualenv not found at $VENV_DIR"
        echo "Run: python -m venv .venv && pip install -e '.[dev]'"
        exit 1
    fi

    # Create logs directory
    mkdir -p "$LOGS_DIR"

    # Generate plists from templates
    for label in "$SERVER_LABEL" "$TICKER_LABEL"; do
        src="$TEMPLATE_DIR/$label.plist"
        dst="$PLIST_DIR/$label.plist"

        if [ ! -f "$src" ]; then
            echo "Error: template not found: $src"
            exit 1
        fi

        sed \
            -e "s|__PROJECT__|$PROJECT_DIR|g" \
            -e "s|__VENV__|$VENV_DIR|g" \
            -e "s|__LOGS__|$LOGS_DIR|g" \
            "$src" > "$dst"

        echo "  Installed $dst"
    done

    # Load agents
    launchctl load "$PLIST_DIR/$SERVER_LABEL.plist" 2>/dev/null || true
    launchctl load "$PLIST_DIR/$TICKER_LABEL.plist" 2>/dev/null || true

    echo ""
    echo "AgentLoop is running."
    echo "  Server log:  $LOGS_DIR/agentloop-server.log"
    echo "  Ticker log:  $LOGS_DIR/agentloop-ticker.log"
    echo ""
    echo "Commands:"
    echo "  launchctl list | grep agentloop   — check status"
    echo "  ./scripts/install-launchd.sh uninstall — stop & remove"
}

uninstall() {
    echo "Removing AgentLoop LaunchAgents..."

    for label in "$SERVER_LABEL" "$TICKER_LABEL"; do
        plist="$PLIST_DIR/$label.plist"
        if [ -f "$plist" ]; then
            launchctl unload "$plist" 2>/dev/null || true
            rm "$plist"
            echo "  Removed $label"
        fi
    done

    echo ""
    echo "LaunchAgents removed. Logs preserved at $LOGS_DIR"
}

case "${1:-}" in
    install)  install ;;
    uninstall) uninstall ;;
    *)
        echo "Usage: $0 {install|uninstall}"
        exit 1
        ;;
esac
