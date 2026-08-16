#!/bin/bash
# DroneMill 24/7 Online Dashboard & Cloudflare HTTPS Tunnel Runner

ROOT="/home/brewuser/projects/dronemill"
LOG_DIR="$ROOT/dashboard"
mkdir -p "$LOG_DIR"

# 1. Start Python Server on port 8888 if not running
if ! pgrep -f "dashboard/server.py" > /dev/null; then
  echo ">> Starting DroneMill Dashboard Server on :8888..."
  nohup python3 "$ROOT/dashboard/server.py" > "$LOG_DIR/server.log" 2>&1 &
  sleep 2
fi

# 2. Start Cloudflare Tunnel if not running
pkill -f "cloudflared tunnel" || true
echo ">> Starting Cloudflare HTTPS Tunnel..."
/tmp/cloudflared tunnel --url http://127.0.0.1:8888 > "$LOG_DIR/tunnel.log" 2>&1 &

# Wait for tunnel URL to appear in logs
echo ">> Waiting for public HTTPS URL..."
for i in {1..15}; do
  URL=$(grep -o 'https://[-a-zA-Z0-9@:%._\+~#=]\+\.trycloudflare\.com' "$LOG_DIR/tunnel.log" | head -n 1 || true)
  if [ -n "$URL" ]; then
    echo "$URL" > "$LOG_DIR/public_url.txt"
    echo "==================================================================="
    echo "✨ DRONEMILL DASHBOARD IS LIVE ONLINE!"
    echo "🔗 Bookmark URL: $URL"
    echo "==================================================================="
    exit 0
  fi
  sleep 1
done

echo "WARN: Could not extract URL immediately, check $LOG_DIR/tunnel.log"
