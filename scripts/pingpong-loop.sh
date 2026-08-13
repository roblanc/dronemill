#!/bin/bash
# Create a seamless forward/reverse video loop without duplicated endpoint frames.
# Usage: ./scripts/pingpong-loop.sh <input> <output> [duration]

set -euo pipefail

INPUT="${1:-}"
OUTPUT="${2:-}"
DURATION="${3:-}"

if [ ! -f "$INPUT" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: $0 <input> <output> [duration]" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate -of default=nw=1:nk=1 "$INPUT")
FRAME_TIME=$(awk -v rate="$FPS" 'BEGIN {split(rate, a, "/"); printf "%.9f", a[2] / a[1]}')
CYCLE="${OUTPUT%.mp4}.cycle.mp4"

ffmpeg -y -nostdin -i "$INPUT" -filter_complex "
  [0:v]fps=${FPS},setpts=PTS-STARTPTS,split=2[forward][reverse_src];
  [forward]trim=start=${FRAME_TIME},setpts=PTS-STARTPTS[fwd];
  [reverse_src]reverse,trim=start=${FRAME_TIME},setpts=PTS-STARTPTS[rev];
  [fwd][rev]concat=n=2:v=1:a=0,format=yuv420p[vout]
" -map "[vout]" -an -c:v libx264 -preset medium -crf 20 -r "$FPS" -movflags +faststart "$CYCLE"

if [ -n "$DURATION" ]; then
  ffmpeg -y -nostdin -stream_loop -1 -i "$CYCLE" -map 0:v:0 -c copy -t "$DURATION" -movflags +faststart "$OUTPUT"
else
  mv "$CYCLE" "$OUTPUT"
fi

echo "Done -> $OUTPUT"
