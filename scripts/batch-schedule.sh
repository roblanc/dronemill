#!/bin/bash
# Batch-schedule N videos from queue.csv. Each row → 1 video, 1 day apart.
# Respects YT API quota (~6 uploads/day). Resumable via .batch_state.
#
# queue.csv format (no header):
#   audio_filename,title,description_filename,pitch
# Example:
#   erebus_raw.mp3,"frozen 169 years | hms erebus | 1h",frozen.txt,0.93
#   void_chant.mp3,"the chant beneath | abyssal ambient",chant.txt,0.87
#
# Usage: ./batch-schedule.sh [max_per_run=5]
# Run multiple times until queue empty. Each call schedules up to max_per_run videos.

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"

MAX="${1:-5}"
QUEUE="$ROOT/queue.csv"
STATE="$ROOT/.batch_state"

if [ ! -f "$QUEUE" ]; then
  echo "ERROR: queue.csv not found at $QUEUE"
  echo "Format per line: audio,title,description_file,pitch"
  exit 1
fi

# Skip already-processed rows
PROCESSED=0
[ -f "$STATE" ] && PROCESSED=$(cat "$STATE")
TOTAL=$(grep -cve '^\s*$' "$QUEUE")
REMAINING=$((TOTAL - PROCESSED))

if [ "$REMAINING" -le 0 ]; then
  echo "Queue empty. $PROCESSED/$TOTAL processed."
  echo "Add more rows to $QUEUE or rm $STATE to re-run."
  exit 0
fi

echo ">> Queue: $TOTAL total, $PROCESSED done, $REMAINING remaining"
echo ">> Scheduling up to $MAX in this run"
echo ""

COUNT=0
while IFS=, read -r AUDIO TITLE DESC PITCH; do
  # Skip processed
  if [ "$COUNT" -lt "$PROCESSED" ]; then
    COUNT=$((COUNT + 1))
    continue
  fi

  # Stop at MAX
  RUN_COUNT=$((COUNT - PROCESSED))
  if [ "$RUN_COUNT" -ge "$MAX" ]; then
    break
  fi

  # Strip quotes/whitespace
  AUDIO=$(echo "$AUDIO" | xargs)
  TITLE=$(echo "$TITLE" | sed 's/^"//;s/"$//' | xargs)
  DESC=$(echo "$DESC" | xargs)
  PITCH=$(echo "$PITCH" | xargs)
  [ -z "$PITCH" ] && PITCH="0.93"

  echo "=========================================="
  echo "[$((COUNT + 1))/$TOTAL] $TITLE"
  echo "=========================================="

  AUDIO_PATH="$ROOT/audio/$AUDIO"
  DESC_PATH="$ROOT/descriptions/$DESC"

  if [ ! -f "$AUDIO_PATH" ]; then
    echo "ERROR: audio not found: $AUDIO_PATH — skipping"
    COUNT=$((COUNT + 1))
    continue
  fi

  if "$DIR/full-pipeline.sh" "$AUDIO_PATH" "$TITLE" "$DESC_PATH" "$PITCH" schedule; then
    COUNT=$((COUNT + 1))
    echo "$COUNT" > "$STATE"
    echo ""
    echo ">> Sleeping 30s before next (avoid YT rate limit)..."
    sleep 30
  else
    echo "ERROR: pipeline failed at row $((COUNT + 1)). State preserved at $COUNT."
    exit 1
  fi
done < "$QUEUE"

DONE=$(cat "$STATE")
LEFT=$((TOTAL - DONE))
echo ""
echo "=========================================="
echo "Batch run complete. Done: $DONE/$TOTAL ($LEFT remaining)"
if [ "$LEFT" -gt 0 ]; then
  echo "Run again tomorrow (quota refreshes daily) or now if YT API still has budget."
fi
