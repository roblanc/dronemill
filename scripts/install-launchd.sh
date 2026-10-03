#!/bin/bash
# Install Dronemill's daily launchd job. Default only copies the plist.
# Use --load to enable the schedule, --unload to disable it.

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/launchd/com.romica.dronemill.plist"
DEST="$HOME/Library/LaunchAgents/com.romica.dronemill.plist"
SERVICE="gui/$(id -u)/com.romica.dronemill"

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs"

case "${1:-install}" in
  install)
    cp "$SRC" "$DEST"
    echo "Installed plist: $DEST"
    echo "Not loaded. Enable with: $0 --load"
    ;;
  --load|load)
    cp "$SRC" "$DEST"
    launchctl bootout "gui/$(id -u)" "$DEST" >/dev/null 2>&1 || true
    launchctl bootstrap "gui/$(id -u)" "$DEST"
    launchctl enable "$SERVICE"
    echo "Loaded daily Dronemill job at 03:00 local."
    ;;
  --unload|unload)
    launchctl bootout "gui/$(id -u)" "$DEST" >/dev/null 2>&1 || true
    echo "Unloaded daily Dronemill job."
    ;;
  *)
    echo "Usage: $0 [install|--load|--unload]" >&2
    exit 1
    ;;
esac
