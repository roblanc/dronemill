#!/bin/bash
# Mix two ambient beds into one source file for cosmic.sh / full-pipeline.
# Usage: ./mix-beds.sh <bed_a> <bed_b> <output_name> [vol_a=0.7] [vol_b=0.35] [duration_sec=3600]
#
# Loops shorter inputs to match duration. Output: audio/queue/<output_name>.mp3

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

A="$1"
B="$2"
NAME="$3"
VOL_A="${4:-0.7}"
VOL_B="${5:-0.35}"
DUR="${6:-3600}"

if [ -z "$A" ] || [ -z "$B" ] || [ -z "$NAME" ]; then
  echo "Usage: $0 <bed_a> <bed_b> <output_name> [vol_a=0.7] [vol_b=0.35] [duration_sec=3600]"
  exit 1
fi

for f in "$A" "$B"; do
  if [ ! -f "$f" ]; then
    echo "ERROR: not found: $f" >&2
    exit 1
  fi
done

OUT_DIR="$ROOT/audio/queue"
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/${NAME}.mp3"

echo ">> Mixing beds -> $OUT (${DUR}s, vol_a=$VOL_A vol_b=$VOL_B)"
ffmpeg -y -nostdin \
  -stream_loop -1 -i "$A" \
  -stream_loop -1 -i "$B" \
  -filter_complex "
    [0:a]volume=${VOL_A},afade=t=in:st=0:d=8,afade=t=out:st=$((DUR - 12)):d=12[a];
    [1:a]volume=${VOL_B},lowpass=f=4000,afade=t=in:st=0:d=12,afade=t=out:st=$((DUR - 12)):d=12[b];
    [a][b]amix=inputs=2:duration=longest:dropout_transition=0,
    lowpass=f=9000,
    acompressor=threshold=0.25:ratio=3:attack=200:release=800
  " \
  -t "$DUR" -c:a libmp3lame -b:a 192k "$OUT"

echo "Done -> $OUT"