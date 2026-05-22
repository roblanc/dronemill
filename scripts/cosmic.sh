#!/bin/bash
# Render 1h cosmic-horror ambient video.
# Usage: ./cosmic.sh <audio> <image> <title> [pitch=0.93]
# Output filename derived from <title> (slugified).
# Example: ./cosmic.sh ../audio/raw.mp3 ../images/cover.png \
#            "frozen 169 years | hms erebus deep ambient | dark arctic drone" 0.93

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"

AUDIO="$1"
IMAGE="$2"
TITLE="$3"
PITCH="${4:-0.93}"

if [ -z "$AUDIO" ] || [ -z "$IMAGE" ] || [ -z "$TITLE" ]; then
  echo "Usage: $0 <audio> <image> <title> [pitch=0.93]"
  exit 1
fi

SLUG=$(slugify "$TITLE")
SHIFTED="$ROOT/output/${SLUG}_shifted.aac"
LOOP60="$ROOT/output/${SLUG}_loop60.mp4"
OUT="$ROOT/output/${SLUG}.mp4"

DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$AUDIO")
LOOPS=$(awk "BEGIN {print int($DUR / 60) + 1}")

SR=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=noprint_wrappers=1:nokey=1 "$AUDIO")
if [ -z "$SR" ] || ! [[ "$SR" =~ ^[0-9]+$ ]]; then
  SR=44100
fi

echo "[1/3] Pitch shift + AAC encode (pitch=$PITCH, sample_rate=$SR)..."
ffmpeg -y -i "$AUDIO" \
  -af "asetrate=${SR}*${PITCH},aresample=${SR},atempo=$(awk "BEGIN {print 1/${PITCH}}"),lowpass=f=8000" \
  -c:a aac -b:a 192k "$SHIFTED"

echo "[2/3] Build 60s still-image clip..."
ffmpeg -y -loop 1 -framerate 1 -t 60 -i "$IMAGE" \
  -c:v libx264 -tune stillimage -preset ultrafast -pix_fmt yuv420p \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black" \
  -r 1 "$LOOP60"

echo "[3/3] Loop x${LOOPS} + mux audio..."
ffmpeg -y -stream_loop "$LOOPS" -i "$LOOP60" -i "$SHIFTED" \
  -c:v copy -c:a copy -shortest \
  -map 0:v:0 -map 1:a:0 "$OUT"

rm "$LOOP60" "$SHIFTED"
echo "Done -> $OUT"
