#!/bin/bash
# Generate titles + descriptions to match audio/image inventory.
# Output: queue.csv ready for batch-schedule.sh
#
# Workflow assumed:
#   1. You drop N audios in audio/queue/
#   2. You drop N images in images/queue/
#   3. Run this → generates N titles + N descriptions, builds queue.csv
#   4. Run batch-schedule.sh
#
# Usage: ./prep-month.sh [count=auto]
# If count omitted, uses min(audio_count, image_count)

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"

read AUDIO_AVAIL IMG_AVAIL <<< "$(count_queue "$ROOT")"

MIN=$AUDIO_AVAIL
[ "$IMG_AVAIL" -lt "$MIN" ] && MIN=$IMG_AVAIL

COUNT="${1:-$MIN}"

echo ">> Inventory: $AUDIO_AVAIL audio, $IMG_AVAIL images in queues"
echo ">> Generating $COUNT title+description pairs..."
echo ""

if [ "$COUNT" -gt "$MIN" ]; then
  echo "WARN: requested $COUNT but only $MIN audio+image pairs available."
  echo "      $COUNT rows will be in queue.csv but only $MIN can be processed."
  echo ""
fi

if [ "$COUNT" -eq 0 ]; then
  echo "ERROR: nothing to generate. Drop audio in audio/queue/ and images in images/queue/."
  exit 1
fi

QUEUE="$ROOT/queue.csv"
if [ -f "$QUEUE" ]; then
  echo ">> Backing up existing queue.csv to queue.csv.bak"
  mv "$QUEUE" "$QUEUE.bak"
fi

# Check Ollama
if ! command -v ollama > /dev/null 2>&1; then
  echo "ERROR: ollama not installed. brew install ollama"
  exit 1
fi

# 1. Generate titles
echo ">> [1/2] Generating titles..."
TITLES_FILE=$(mktemp)
python3 "$DIR/gen-titles.py" "$COUNT" mixed > "$TITLES_FILE"

# 2. Per title: generate description, append to queue.csv
echo ""
echo ">> [2/2] Generating descriptions via Ollama (qwen3.5:9b)..."
> "$QUEUE"
i=0
PITCHES=("0.85" "0.91" "0.93" "1.07")

while IFS= read -r TITLE; do
  i=$((i + 1))
  SLUG=$(slugify "$TITLE")
  DESC_FILE="${SLUG}.txt"
  DESC_PATH="$ROOT/descriptions/${DESC_FILE}"
  PITCH="${PITCHES[$((i % 4))]}"

  echo ""
  echo "[$i/$COUNT] $TITLE"

  if [ -f "$DESC_PATH" ]; then
    echo "   desc: exists, skipping"
  else
    echo "   desc: generating..."
    "$DIR/gen-description.sh" "$TITLE" > "$DESC_PATH"
  fi

  echo "\"$TITLE\",$DESC_FILE,$PITCH" >> "$QUEUE"
done < "$TITLES_FILE"

rm "$TITLES_FILE"

echo ""
echo "=========================================="
echo "DONE. queue.csv has $i rows."
echo ""
echo "Next:"
echo "  cat queue.csv     # review"
echo "  ./scripts/batch-schedule.sh 5"
echo "=========================================="
