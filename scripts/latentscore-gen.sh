#!/bin/bash
# Generate a title-conditioned ambient WAV with LatentScore in Docker.
# Usage: ./scripts/latentscore-gen.sh <prompt> [output] [duration_seconds]

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
PROMPT="${1:-}"
OUTPUT="${2:-$ROOT/audio/queue/latentscore.wav}"
DURATION="${3:-180}"
IMAGE="dronemill-latentscore:0.1.8"

if [ -z "$PROMPT" ]; then
  echo "Usage: $0 <prompt> [output] [duration_seconds]" >&2
  exit 1
fi

case "$OUTPUT" in
  "$ROOT"/*) ;;
  *) OUTPUT="$ROOT/${OUTPUT#./}" ;;
esac

mkdir -p "$(dirname "$OUTPUT")" "$ROOT/.cache/huggingface"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker build -t "$IMAGE" "$ROOT/tools/latentscore"
fi

ARGS=("$PROMPT" "/work/${OUTPUT#$ROOT/}" --duration "$DURATION")

docker run --rm \
  -v "$ROOT:/work" \
  -v "$ROOT/.cache/huggingface:/root/.cache/huggingface" \
  -e HF_HOME=/root/.cache/huggingface \
  "$IMAGE" "${ARGS[@]}"

ffmpeg -y -i "$OUTPUT" \
  -af "highpass=f=25,lowpass=f=15000,loudnorm=I=-18:TP=-1.5:LRA=9,aformat=channel_layouts=stereo" \
  -ar 48000 "${OUTPUT%.wav}.mastered.wav"

echo "Done -> ${OUTPUT%.wav}.mastered.wav"
