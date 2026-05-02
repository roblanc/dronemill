#!/bin/bash
# Generate original ambient noise (zero copyright risk)
# Usage: ./noise-gen.sh <duration_seconds> <output_name> [color=brown]
# Colors: white, pink, brown
set -e
DUR="${1:-3600}"
NAME="${2:-ambient}"
COLOR="${3:-brown}"

DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$DIR/audio/${NAME}.mp3"

ffmpeg -y -f lavfi -i "anoisesrc=d=${DUR}:c=${COLOR}:r=44100:a=0.15" \
  -af "lowpass=f=600,aecho=0.8:0.7:1500:0.4" \
  -c:a libmp3lame -b:a 192k "$OUT"

echo "Generated $DUR sec $COLOR noise -> $OUT"
