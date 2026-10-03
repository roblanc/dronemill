#!/bin/bash
# Produce/schedule exactly one Dronemill video for the current day.
# Safe for launchd: locked, logged, and duplicate-protected by state/daily.json.
#
# Usage:
#   ./scripts/daily-autopilot.sh
#   ./scripts/daily-autopilot.sh --force
#   ./scripts/daily-autopilot.sh --dry-run

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
STATE_DIR="$ROOT/state"
LOG_DIR="$ROOT/logs"
DAILY_STATE="$STATE_DIR/daily.json"
LOCKFILE="$STATE_DIR/daily.lock"
TODAY="$(date +%Y-%m-%d)"
FORCE=0
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    *) echo "Usage: $0 [--force] [--dry-run]" >&2; exit 1 ;;
  esac
done

mkdir -p "$STATE_DIR" "$LOG_DIR"
export HOME="${HOME:-/Users/romica}"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

if [ -f "$LOCKFILE" ]; then
  PID=$(cat "$LOCKFILE" 2>/dev/null || true)
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "ERROR: daily autopilot already running (PID $PID)" >&2
    exit 1
  fi
fi
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ROOT/.env"
  set +a
fi

LAST_SUCCESS=$(python3 - "$DAILY_STATE" <<'PY'
import json, os, sys
path = sys.argv[1]
if not os.path.exists(path):
    print("")
    raise SystemExit
try:
    print(json.load(open(path)).get("last_success_date", ""))
except Exception:
    print("")
PY
)

if [ "$FORCE" -eq 0 ] && [ "$LAST_SUCCESS" = "$TODAY" ]; then
  echo "already_done: $TODAY"
  exit 0
fi

LOG_FILE="$LOG_DIR/daily_autopilot_${TODAY}_$(date +%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== DAILY AUTOPILOT START: $(date) ==="
echo "root: $ROOT"
echo "log:  $LOG_FILE"

if [ "$DRY_RUN" -eq 1 ]; then
  "$DIR/doctor.sh"
  python3 "$DIR/stock-manager.py" --min-images 1 --min-queue 1 --dry-run
  echo "dry_run: would run ./scripts/batch-schedule.sh 1"
  exit 0
fi

"$DIR/doctor.sh"
python3 "$DIR/stock-manager.py" --min-images 1 --min-queue 1
"$DIR/doctor.sh" --stock

RUN_LOG=$(mktemp "${TMPDIR:-/tmp}/dronemill_daily.XXXXXX")
if "$DIR/batch-schedule.sh" 1 | tee "$RUN_LOG"; then
  if grep -q "Run complete. 1 scheduled." "$RUN_LOG"; then
    python3 - "$DAILY_STATE" "$TODAY" "$LOG_FILE" <<'PY'
import json, os, sys
path, today, log_file = sys.argv[1:4]
data = {}
if os.path.exists(path):
    try:
        data = json.load(open(path))
    except Exception:
        data = {}
data.update({
    "last_success_date": today,
    "target_per_day": 1,
    "last_log": log_file,
})
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
PY
    echo "scheduled: $TODAY"
    rm -f "$RUN_LOG"
    echo "=== DAILY AUTOPILOT SUCCESS: $(date) ==="
    exit 0
  fi
  echo "ERROR: batch-schedule exited cleanly but did not schedule one video" >&2
  cat "$RUN_LOG" >&2
  rm -f "$RUN_LOG"
  exit 1
fi

STATUS=$?
cat "$RUN_LOG" >&2 || true
rm -f "$RUN_LOG"
echo "=== DAILY AUTOPILOT FAILED: $(date) ==="
exit "$STATUS"
