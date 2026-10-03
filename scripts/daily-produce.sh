#!/bin/bash
# Cron-ready wrapper for daily video generation and uploading.
# Automatically sources, renders, and schedules one video.

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
LOG_DIR="$ROOT/logs"
LOCKFILE="/tmp/dronemill_daily.lock"

# 1. Ensure logs directory exists
mkdir -p "$LOG_DIR"

# 2. Prevent concurrent executions
if [ -f "$LOCKFILE" ]; then
  PID=$(cat "$LOCKFILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "$(date): ERROR - Another daily run is already in progress (PID $PID)." >> "$LOG_DIR/error.log"
    exit 1
  fi
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT

# 3. Setup environment
export HOME="/Users/romica"
export PYTHONPATH="/Users/romica/Library/Python/3.9/lib/python/site-packages:$PYTHONPATH"
export OLLAMA_MODEL="qwen2.5:1.5b"
# Load Homebrew paths for utilities
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# 4. Generate log filename with current date
LOG_FILE="$LOG_DIR/daily_$(date +%Y-%m-%d_%H-%M-%S).log"

echo "=== DAILY PRODUCE RUN START: $(date) ===" > "$LOG_FILE"

source "$DIR/_lib.sh"
if ! require_disk_space 10 "$ROOT/output"; then
  echo "$(date): ERROR - insufficient disk space for render (need 10GB+ free)." >> "$LOG_DIR/error.log"
  exit 1
fi

# 5. Run batch scheduler and redirect output to log
if /bin/bash "$DIR/batch-schedule.sh" 1 >> "$LOG_FILE" 2>&1; then
  echo "=== DAILY PRODUCE SUCCESS: $(date) ===" >> "$LOG_FILE"
  # Keep only last 30 log files
  find "$LOG_DIR" -name "daily_*.log" -type f -mtime +30 -delete
  exit 0
else
  echo "=== DAILY PRODUCE FAILED: $(date) ===" >> "$LOG_FILE"
  echo "Check log at: $LOG_FILE" >&2
  # Append failure notice to error log
  echo "$(date): daily-produce.sh failed. Log: $LOG_FILE" >> "$LOG_DIR/error.log"
  exit 1
fi
