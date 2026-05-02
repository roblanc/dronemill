#!/bin/bash
# Full pipeline: pick image from queue → render → upload → mark image used.
# Usage: ./full-pipeline.sh <audio> <title> <desc_file> [pitch=0.93] [privacy=unlisted]
# Example:
#   ./full-pipeline.sh \
#     ../audio/erebus_raw.mp3 \
#     "signals from below | hms erebus abyssal ambient | 1 hour" \
#     ../descriptions/signals.txt \
#     0.91

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"

AUDIO="$1"
TITLE="$2"
DESC="$3"
PITCH="${4:-0.93}"
PRIVACY="${5:-unlisted}"

if [ -z "$AUDIO" ] || [ -z "$TITLE" ] || [ -z "$DESC" ]; then
  echo "Usage: $0 <audio> <title> <desc_file> [pitch=0.93] [privacy=unlisted]"
  exit 1
fi

SLUG=$(slugify "$TITLE")
IMAGE=$(next_image "$ROOT")
echo ">> Title: $TITLE"
echo ">> Slug:  $SLUG"
echo ">> Image: $IMAGE"

echo ""
echo "=== STAGE 1: render ==="
"$DIR/cosmic.sh" "$AUDIO" "$IMAGE" "$TITLE" "$PITCH"

VIDEO="$ROOT/output/${SLUG}.mp4"

echo ""
echo "=== STAGE 2: youtube upload ==="
"$DIR/upload-yt.sh" "$VIDEO" "$TITLE" "$DESC" "$IMAGE" "$PRIVACY"

echo ""
echo "=== STAGE 3: mark image used ==="
mark_used "$IMAGE" "$ROOT"

echo ""
echo "=== DONE ==="
echo "Local: $VIDEO"
echo "YT:    uploaded as '$PRIVACY'. Check https://studio.youtube.com"
