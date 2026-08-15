#!/bin/bash
# Render only — pick image from queue, render, mark used. No YT upload.
# Usage: ./render-only.sh <audio> <title> [pitch=0.93]

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"

AUDIO="$1"
TITLE="$2"
PITCH="${3:-0.93}"

if [ -z "$AUDIO" ] || [ -z "$TITLE" ]; then
  echo "Usage: $0 <audio> <title> [pitch=0.93]"
  exit 1
fi

SLUG=$(slugify "$TITLE")
IMAGE=$(next_image "$ROOT")
echo ">> Title: $TITLE"
echo ">> Slug:  $SLUG"
echo ">> Image: $IMAGE"

"$DIR/cosmic.sh" "$AUDIO" "$IMAGE" "$TITLE" "$PITCH"
mark_used "$IMAGE" "$ROOT"

echo "Done -> $DRONEMILL_MEDIA_DIR/${SLUG}.mp4"
