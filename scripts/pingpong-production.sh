#!/bin/bash
# Loop a ping-pong visual cycle against long-form audio without video re-encoding.
# Usage: ./scripts/pingpong-production.sh <visual-cycle.mp4> <audio> <output.mp4> [duration=7200]

set -euo pipefail

VISUAL="${1:-}"
AUDIO="${2:-}"
OUTPUT="${3:-}"
DURATION="${4:-7200}"

if [ ! -f "$VISUAL" ] || [ ! -f "$AUDIO" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: $0 <visual-cycle.mp4> <audio> <output.mp4> [duration=7200]" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
ffmpeg -y -nostdin -stream_loop -1 -i "$VISUAL" -i "$AUDIO" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -t "$DURATION" -movflags +faststart "$OUTPUT"

echo "Done -> $OUTPUT"
