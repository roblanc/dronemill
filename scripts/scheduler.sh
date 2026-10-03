#!/bin/bash
# Pick next available scheduling slot for the channel.
# Usage: ./scheduler.sh [hour=18] [tz_offset_hours=3]
# Logic:
#   - Reads SCHEDULE_STATE_FILE for last scheduled timestamp
#   - Returns next slot at <hour> local-time, advancing 1 day per call
#   - Default: 18:00 EEST (UTC+3) = 15:00 UTC
# Output: ISO 8601 UTC timestamp (e.g. 2026-05-04T15:00:00Z)
# Use as: PUB=$(./scheduler.sh) && ./upload-yt.sh ... "$PUB"

set -e

# Auto-detect local timezone offset in hours
OFFSET_STR=$(date +%z)
SIGN="${OFFSET_STR:0:1}"
HOURS="${OFFSET_STR:1:2}"
HOURS=$(echo "$HOURS" | sed 's/^0//')
[ -z "$HOURS" ] && HOURS=0

if [ "$SIGN" = "-" ]; then
  DETECTED_TZ_OFFSET=$(( -HOURS ))
else
  DETECTED_TZ_OFFSET=$(( HOURS ))
fi

HOUR_LOCAL="${1:-18}"
TZ_OFFSET="${2:-$DETECTED_TZ_OFFSET}"

DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$DIR/.schedule_state"

# Calculate UTC hour
HOUR_UTC=$((HOUR_LOCAL - TZ_OFFSET))
if [ "$HOUR_UTC" -lt 0 ]; then
  HOUR_UTC=$((HOUR_UTC + 24))
fi

# Read last scheduled timestamp; if none, use today
if [ -f "$STATE" ]; then
  LAST=$(cat "$STATE")
  # Parse last + add 1 day
  if date -j > /dev/null 2>&1; then
    # macOS BSD date
    NEXT_DATE=$(date -j -v+1d -f "%Y-%m-%dT%H:%M:%SZ" "$LAST" +"%Y-%m-%d")
  else
    # GNU date
    NEXT_DATE=$(date -d "$LAST +1 day" +"%Y-%m-%d")
  fi
else
  # First run: schedule for today (or tomorrow if hour passed)
  NOW_HOUR=$(date -u +"%H")
  if [ "$NOW_HOUR" -ge "$HOUR_UTC" ]; then
    if date -j > /dev/null 2>&1; then
      NEXT_DATE=$(date -j -v+1d +"%Y-%m-%d")
    else
      NEXT_DATE=$(date -d "tomorrow" +"%Y-%m-%d")
    fi
  else
    NEXT_DATE=$(date -u +"%Y-%m-%d")
  fi
fi

NEXT="${NEXT_DATE}T$(printf '%02d' $HOUR_UTC):00:00Z"

schedule_epoch() {
  local ts="$1"
  if date -j -f "%Y-%m-%dT%H:%M:%SZ" "$ts" +%s >/dev/null 2>&1; then
    date -j -f "%Y-%m-%dT%H:%M:%SZ" "$ts" +%s
  else
    date -d "$ts" +%s
  fi
}

schedule_add_day() {
  local ts="$1"
  if date -j > /dev/null 2>&1; then
    date -j -v+1d -f "%Y-%m-%dT%H:%M:%SZ" "$ts" +"%Y-%m-%dT%H:%M:%SZ"
  else
    date -d "$ts +1 day" -u +"%Y-%m-%dT%H:%M:%SZ"
  fi
}

NOW_EPOCH=$(date -u +%s)
while [ "$(schedule_epoch "$NEXT")" -le "$NOW_EPOCH" ]; do
  NEXT=$(schedule_add_day "$NEXT")
done

if [ "${SCHEDULE_STATE_WRITE:-1}" != "0" ]; then
  echo "$NEXT" > "$STATE"
fi
echo "$NEXT"
