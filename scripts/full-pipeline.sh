#!/bin/bash
# Full pipeline: pick image from queue → render → upload (optionally scheduled) → mark image used.
# Usage:
#   ./full-pipeline.sh <audio> <title> <desc_file> [pitch=0.93] [mode=schedule|now] [extra]
#   mode=schedule (default): auto-schedules at next slot via scheduler.sh
#   mode=now:                uploads immediately as 'unlisted' (or pass [extra]=public/private)
# Examples:
#   ./full-pipeline.sh ../audio/raw.mp3 "title" ../descriptions/d.txt 0.93 schedule
#   ./full-pipeline.sh ../audio/raw.mp3 "title" ../descriptions/d.txt 0.93 now public

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"

AUDIO="$1"
TITLE="$2"
DESC="$3"
PITCH="${4:-0.93}"
MODE="${5:-schedule}"
EXTRA="${6:-unlisted}"

if [ -z "$AUDIO" ] || [ -z "$TITLE" ] || [ -z "$DESC" ]; then
  echo "Usage: $0 <audio> <title> <desc_file> [pitch=0.93] [mode=schedule|now] [extra]"
  exit 1
fi

SLUG=$(slugify "$TITLE")
IMAGE=$(next_image "$ROOT")
echo ">> Title: $TITLE"
echo ">> Slug:  $SLUG"
echo ">> Image: $IMAGE"
echo ">> Mode:  $MODE"

echo ""
echo "=== STAGE 1: render ==="
"$DIR/cosmic.sh" "$AUDIO" "$IMAGE" "$TITLE" "$PITCH"

VIDEO="$ROOT/output/${SLUG}.mp4"

echo ""
echo "=== STAGE 2: youtube upload ==="
DEFAULT_TAGS="ambient,cosmic horror,dark ambient,sleep ambient,study music,1 hour ambient,sci-fi ambient,deep space,timeless ambience"

if [ "$MODE" = "schedule" ]; then
  PUB=$("$DIR/scheduler.sh")
  echo ">> Publish at: $PUB UTC"
  "$DIR/upload-yt.sh" "$VIDEO" "$TITLE" "$DESC" "$IMAGE" "private" "$DEFAULT_TAGS" "$PUB"
else
  "$DIR/upload-yt.sh" "$VIDEO" "$TITLE" "$DESC" "$IMAGE" "$EXTRA" "$DEFAULT_TAGS" ""
fi

echo ""
echo "=== STAGE 3: mark image used ==="
mark_used "$IMAGE" "$ROOT"

echo ""
echo "=== DONE ==="
echo "Local: $VIDEO"
if [ "$MODE" = "schedule" ]; then
  echo "YT:    scheduled for $PUB UTC. Check https://studio.youtube.com"
else
  echo "YT:    uploaded ($EXTRA). Check https://studio.youtube.com"
fi
