#!/bin/bash
# Batch-schedule N videos. Each row consumes:
#   - 1 audio from audio/queue/ (oldest first)
#   - 1 image from images/queue/ (oldest first)
#   - 1 title + pitch from queue.csv
#
# queue.csv format (no header):
#   title,description_filename,pitch
#   OR:
#   audio_filename,title,description_filename,pitch
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
  echo "Or: audio_filename,title,description_filename,pitch"
  exit 1
fi

PROCESSED=0
[ -f "$STATE" ] && PROCESSED=$(cat "$STATE")

# Run Python parser to perform pre-flight checks and output standardized TSV
PARSED_DATA=$(python3 - "$QUEUE" "$ROOT" "$PROCESSED" "$MAX" <<'EOF'
import os, csv, sys

queue_path = sys.argv[1]
root_dir = sys.argv[2]
processed = int(sys.argv[3])
max_limit = int(sys.argv[4])

# Get available images
images_dir = os.path.join(root_dir, "images", "queue")
if os.path.exists(images_dir):
    images = sorted([f for f in os.listdir(images_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
else:
    images = []

# Get available audio files in audio/queue/
audio_queue_dir = os.path.join(root_dir, "audio", "queue")
if os.path.exists(audio_queue_dir):
    audio_queue_files = sorted([f for f in os.listdir(audio_queue_dir) if f.lower().endswith(('.mp3', '.wav', '.flac', '.m4a'))])
else:
    audio_queue_files = []

available_audio_queue = list(audio_queue_files)
available_images = list(images)

rows = []
try:
    with open(queue_path, "r", encoding="utf-8") as f:
        for r in csv.reader(f):
            if not r or not any(x.strip() for x in r):
                continue
            r = [x.strip() for x in r]
            if len(r) == 3:
                rows.append(("", r[0], r[1], r[2]))
            elif len(r) >= 4:
                rows.append((r[0], r[1], r[2], r[3]))
except Exception as e:
    sys.stderr.write(f"Error parsing CSV: {e}\n")
    sys.exit(1)

total = len(rows)
possible = 0
run_count = 0

for i in range(processed, total):
    if run_count >= max_limit:
        break
    
    audio_col, title, desc, pitch = rows[i]
    desc_path = os.path.join(root_dir, "descriptions", desc)
    if not os.path.exists(desc_path):
        continue
        
    if not available_images:
        break
        
    if audio_col:
        if audio_col in available_audio_queue:
            available_audio_queue.remove(audio_col)
        elif os.path.exists(os.path.join(root_dir, "audio", audio_col)):
            pass
        else:
            break
    else:
        if not available_audio_queue:
            break
        available_audio_queue.pop(0)
        
    available_images.pop(0)
    possible += 1
    run_count += 1

print(total)
print(possible)
print(len(audio_queue_files))
print(len(images))
for r in rows:
    print("\t".join(r))
EOF
)

TOTAL=$(echo "$PARSED_DATA" | sed -n '1p')
POSSIBLE=$(echo "$PARSED_DATA" | sed -n '2p')
AUDIO_AVAIL=$(echo "$PARSED_DATA" | sed -n '3p')
IMG_AVAIL=$(echo "$PARSED_DATA" | sed -n '4p')
PARSED_ROWS=$(echo "$PARSED_DATA" | tail -n +5)
REMAINING=$((TOTAL - PROCESSED))

echo ">> Queue:    $TOTAL total rows, $PROCESSED done, $REMAINING remaining"
echo ">> Audio:    $AUDIO_AVAIL files in audio/queue/"
echo ">> Images:   $IMG_AVAIL files in images/queue/"
echo ">> Max run:  $MAX videos"
echo ""

if [ "$REMAINING" -le 0 ]; then
  echo "Queue empty. Add rows to $QUEUE or rm $STATE to re-run."
  exit 0
fi

if [ "$IMG_AVAIL" -eq 0 ]; then
  echo "ERROR: images/queue/ empty. Drop .png/.jpg files there first."
  exit 1
fi

if [ "$POSSIBLE" -eq 0 ] && [ "$REMAINING" -gt 0 ]; then
  echo "ERROR: Cannot schedule any videos. Check that description files exist and you have enough audio/images in queue."
  exit 1
fi

if [ "$POSSIBLE" -lt "$MAX" ] && [ "$POSSIBLE" -lt "$REMAINING" ]; then
  echo "WARN: limited to $POSSIBLE videos this run (queue/audio/images bottleneck or missing description files)"
fi
echo ""

COUNT=0
RUN_COUNT=0
while IFS=$'\t' read -r AUDIO_COL TITLE DESC PITCH; do
  if [ "$COUNT" -lt "$PROCESSED" ]; then
    COUNT=$((COUNT + 1))
    continue
  fi

  if [ "$RUN_COUNT" -ge "$POSSIBLE" ]; then
    break
  fi

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

  # Resolve audio file
  if [ -n "$AUDIO_COL" ]; then
    if [ -f "$ROOT/audio/queue/$AUDIO_COL" ]; then
      AUDIO="$ROOT/audio/queue/$AUDIO_COL"
    elif [ -f "$ROOT/audio/$AUDIO_COL" ]; then
      AUDIO="$ROOT/audio/$AUDIO_COL"
    else
      echo "ERROR: audio file not found: $AUDIO_COL (checked in audio/queue/ and audio/) — skipping row"
      COUNT=$((COUNT + 1))
      continue
    fi
  else
    AUDIO=$(next_audio "$ROOT")
  fi

  echo ">> Audio:  $AUDIO"

  if "$DIR/full-pipeline.sh" "$AUDIO" "$TITLE" "$DESC_PATH" "$PITCH" schedule; then
    if [[ "$AUDIO" == "$ROOT/audio/queue/"* ]]; then
      mark_audio_used "$AUDIO" "$ROOT"
    else
      echo ">> Using shared audio, not moving to used/"
    fi
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
done <<< "$PARSED_ROWS"

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
