#!/bin/bash
# Report scheduled runway and optionally invoke a configured replenishment command.
# Usage: ./scripts/rolling-batch-check.sh [minimum_days=7] [target_days=30] [--run]

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
MINIMUM_DAYS="${1:-7}"
TARGET_DAYS="${2:-30}"
MODE="${3:---dry-run}"
STATE="$ROOT/.schedule_state"
LOCK="$ROOT/.rolling-batch.lock"

if [ -f "$STATE" ]; then
  LAST="$(cat "$STATE")"
  LAST_EPOCH="$(date -d "$LAST" +%s)"
  NOW_EPOCH="$(date -u +%s)"
  RUNWAY_DAYS=$(( (LAST_EPOCH - NOW_EPOCH + 86399) / 86400 ))
  [ "$RUNWAY_DAYS" -lt 0 ] && RUNWAY_DAYS=0
else
  RUNWAY_DAYS=0
fi

NEEDED=$((TARGET_DAYS - RUNWAY_DAYS))
[ "$NEEDED" -lt 0 ] && NEEDED=0
echo "Scheduled runway: ${RUNWAY_DAYS} days; target: ${TARGET_DAYS}; needed: ${NEEDED}"

if [ "$RUNWAY_DAYS" -ge "$MINIMUM_DAYS" ] || [ "$NEEDED" -eq 0 ]; then
  exit 0
fi

if [ "$MODE" != "--run" ]; then
  echo "DRY RUN: replenishment required. Configure DRONEMILL_BATCH_COMMAND before using --run."
  exit 0
fi

if [ -z "${DRONEMILL_BATCH_COMMAND:-}" ]; then
  echo "ERROR: DRONEMILL_BATCH_COMMAND is not configured" >&2
  exit 1
fi

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "ERROR: another rolling batch is running" >&2
  exit 1
fi

export DRONEMILL_BATCH_COUNT="$NEEDED"
exec bash -lc "$DRONEMILL_BATCH_COMMAND"
