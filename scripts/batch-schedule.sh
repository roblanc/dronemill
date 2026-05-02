#!/bin/bash
# Batch-schedule N videos. Each row consumes:
#   - 1 audio from audio/queue/ (oldest first)
#   - 1 image from images/queue/ (oldest first)
#   - 1 title + pitch from queue.csv
#
# queue.csv format (no header):
#   title,description_filename,pitch
# Example:
#   "He Was Already Waiting Behind the Door…",door.txt,0.93
#
# Resumable via .batch_state.
# Usage: ./batch-schedule.sh [max_per_run=5]

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"

MAX="${1:-5}"
QUEUE="$ROOT/queue.csv"
STATE="$ROOT/.batch_state"

if [ ! -f "$QUEUE" ]; then
  echo "ERROR: queue.csv not found at $QUEUE"
  echo "Format per line: title,description_filename,pitch"
  exit 1
fi

PROCESSED=0
[ -f "$STATE" ] && PROCESSED=$(cat "$STATE")
TOTAL=$(grep -cve '^\s*$' "$QUEUE")
REMAINING=$((TOTAL - PROCESSED))

# Pre-flight: count queue inventory
read AUDIO_AVAIL IMG_AVAIL <<< "$(count_queue "$ROOT")"

echo ">> Queue:    $TOTAL total rows, $PROCESSED done, $REMAINING remaining"
echo ">> Audio:    $AUDIO_AVAIL files in audio/queue/"
echo ">> Images:   $IMG_AVAIL files in images/queue/"
echo ">> Max run:  $MAX videos"
echo ""

if [ "$REMAINING" -le 0 ]; then
  echo "Queue empty. Add rows to $QUEUE or rm $STATE to re-run."
  exit 0
fi

if [ "$AUDIO_AVAIL" -eq 0 ]; then
  echo "ERROR: audio/queue/ empty. Drop .mp3 files there first."
  exit 1
fi

if [ "$IMG_AVAIL" -eq 0 ]; then
  echo "ERROR: images/queue/ empty. Drop .png/.jpg files there first."
  exit 1
fi

POSSIBLE=$REMAINING
[ "$AUDIO_AVAIL" -lt "$POSSIBLE" ] && POSSIBLE=$AUDIO_AVAIL
[ "$IMG_AVAIL" -lt "$POSSIBLE" ] && POSSIBLE=$IMG_AVAIL
[ "$MAX" -lt "$POSSIBLE" ] && POSSIBLE=$MAX

if [ "$POSSIBLE" -lt "$MAX" ]; then
  echo "WARN: limited to $POSSIBLE videos this run (queue/audio/images bottleneck)"
fi
echo ""

COUNT=0
RUN_COUNT=0
while IFS=, read -r TITLE DESC PITCH; do
  if [ "$COUNT" -lt "$PROCESSED" ]; then
    COUNT=$((COUNT + 1))
    continue
  fi

  if [ "$RUN_COUNT" -ge "$POSSIBLE" ]; then
    break
  fi

  TITLE=$(echo "$TITLE" | sed 's/^"//;s/"$//' | xargs)
  DESC=$(echo "$DESC" | xargs)
  PITCH=$(echo "$PITCH" | xargs)
  [ -z "$PITCH" ] && PITCH="0.93"

  echo "=========================================="
  echo "[$((COUNT + 1))/$TOTAL] $TITLE"
  echo "=========================================="

  DESC_PATH="$ROOT/descriptions/$DESC"
  if [ ! -f "$DESC_PATH" ]; then
    echo "ERROR: description not found: $DESC_PATH — skipping row"
    COUNT=$((COUNT + 1))
    continue
  fi

  AUDIO=$(next_audio "$ROOT")
  echo ">> Audio:  $AUDIO"

  if "$DIR/full-pipeline.sh" "$AUDIO" "$TITLE" "$DESC_PATH" "$PITCH" schedule; then
    mark_audio_used "$AUDIO" "$ROOT"
    COUNT=$((COUNT + 1))
    RUN_COUNT=$((RUN_COUNT + 1))
    echo "$COUNT" > "$STATE"
    echo ""
    if [ "$RUN_COUNT" -lt "$POSSIBLE" ]; then
      echo ">> Sleeping 30s before next..."
      sleep 30
    fi
  else
    echo "ERROR: pipeline failed at row $((COUNT + 1)). State preserved at $COUNT."
    exit 1
  fi
done < "$QUEUE"

DONE=$(cat "$STATE")
LEFT=$((TOTAL - DONE))
echo ""
echo "=========================================="
echo "Run complete. $RUN_COUNT scheduled. Total: $DONE/$TOTAL ($LEFT remaining)"
if [ "$LEFT" -gt 0 ]; then
  read AUD_LEFT IMG_LEFT <<< "$(count_queue "$ROOT")"
  echo "Stock: $AUD_LEFT audio, $IMG_LEFT images in queues"
  echo "Run again tomorrow (YT quota refreshes daily)"
fi
