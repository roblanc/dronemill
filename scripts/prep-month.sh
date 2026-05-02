#!/bin/bash
# Generate a full month of content scaffolding: audios + titles + descriptions + queue.csv.
# Images you must drop manually in images/queue/ (or generate via ComfyUI/SD locally).
#
# Usage: ./prep-month.sh [count=30]
# Output:
#   audio/ambient_001.mp3 ... audio/ambient_030.mp3   (procedural)
#   descriptions/<slug>.txt × 30                       (Ollama-generated)
#   queue.csv                                          (ready for batch-schedule.sh)

set -e

COUNT="${1:-30}"
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"

QUEUE="$ROOT/queue.csv"

if [ -f "$QUEUE" ]; then
  echo "WARN: $QUEUE exists. Backing up to queue.csv.bak"
  mv "$QUEUE" "$QUEUE.bak"
fi

echo ">> Preparing $COUNT videos worth of content..."

# 1) Generate $COUNT titles
echo ">> [1/3] Generating $COUNT titles..."
TITLES_FILE=$(mktemp)
python3 "$DIR/gen-titles.py" "$COUNT" mixed > "$TITLES_FILE"
echo "   $(wc -l < "$TITLES_FILE") titles ready"

# 2) Generate audio + description per title
echo ""
echo ">> [2/3] Generating audio + descriptions (Ollama running locally)..."

i=0
> "$QUEUE"
while IFS= read -r TITLE; do
  i=$((i + 1))
  PADDED=$(printf "%03d" $i)
  AUDIO_NAME="ambient_${PADDED}"
  AUDIO_FILE="${AUDIO_NAME}.mp3"
  SLUG=$(slugify "$TITLE")
  DESC_FILE="${SLUG}.txt"
  DESC_PATH="$ROOT/descriptions/${DESC_FILE}"

  echo ""
  echo "[$i/$COUNT] $TITLE"

  # Audio: skip if exists
  if [ -f "$ROOT/audio/$AUDIO_FILE" ]; then
    echo "   audio: exists, skipping"
  else
    echo "   audio: synthesizing..."
    "$DIR/audio-synth.sh" 3600 "$AUDIO_NAME" "$i" > /dev/null 2>&1
  fi

  # Description: skip if exists
  if [ -f "$DESC_PATH" ]; then
    echo "   desc: exists, skipping"
  else
    echo "   desc: generating via Ollama..."
    "$DIR/gen-description.sh" "$TITLE" > "$DESC_PATH"
  fi

  # Random pitch from set
  PITCHES=("0.85" "0.91" "0.93" "1.07")
  PITCH="${PITCHES[$((i % 4))]}"

  # CSV row
  echo "$AUDIO_FILE,\"$TITLE\",$DESC_FILE,$PITCH" >> "$QUEUE"
done < "$TITLES_FILE"

rm "$TITLES_FILE"

echo ""
echo ">> [3/3] queue.csv built — $i rows"
echo ""
echo "=========================================="
echo "DONE. Now:"
echo "  1. Drop $COUNT images in images/queue/ (Stable Diffusion or manual)"
echo "  2. Review queue.csv if needed"
echo "  3. Run: ./scripts/batch-schedule.sh 5"
echo "     (5/day until queue empty due to YT API quota)"
echo "=========================================="
