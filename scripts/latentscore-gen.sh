#!/bin/bash
# Generate a title-conditioned ambient WAV with LatentScore in Docker.
# Usage:
#   ./scripts/latentscore-gen.sh <prompt> [output] [duration_seconds] [--natural] [--no-lead]
#   ./scripts/latentscore-gen.sh --preset <name> [output] [duration_seconds] [--natural] [--no-lead]

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
IMAGE="dronemill-latentscore:0.1.8"

PRESET=""
if [ "${1:-}" = "--preset" ]; then
  PRESET="${2:-}"
  shift 2
fi

if [ -n "$PRESET" ]; then
  OUTPUT="${1:-$ROOT/audio/queue/latentscore.wav}"
  DURATION="${2:-180}"
  shift 2 2>/dev/null || true
else
  PROMPT="${1:-}"
  OUTPUT="${2:-$ROOT/audio/queue/latentscore.wav}"
  DURATION="${3:-180}"
  shift 3 2>/dev/null || true
fi

NATURAL=""
NO_LEAD=""
for extra in "$@"; do
  case "$extra" in
    --natural) NATURAL="--natural" ;;
    --no-lead) NO_LEAD="--no-lead" ;;
    *) echo "unexpected argument: $extra" >&2; exit 1 ;;
  esac
done

case "$OUTPUT" in
  "$ROOT"/*) ;;
  *) OUTPUT="$ROOT/${OUTPUT#./}" ;;
esac

mkdir -p "$(dirname "$OUTPUT")" "$ROOT/.cache/huggingface"

if [ -n "$PRESET" ]; then
  ARGS=(--preset "$PRESET" "/work/${OUTPUT#$ROOT/}" --duration "$DURATION" $NATURAL $NO_LEAD)
elif [ -n "$PROMPT" ]; then
  ARGS=("$PROMPT" "/work/${OUTPUT#$ROOT/}" --duration "$DURATION" $NATURAL $NO_LEAD)
else
  echo "Usage: $0 <prompt>|--preset <name> [output] [duration_seconds] [--natural] [--no-lead]" >&2
  exit 1
fi

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker build -t "$IMAGE" "$ROOT/tools/latentscore"
fi

docker run --rm \
  -v "$ROOT:/work" \
  -v "$ROOT/.cache/huggingface:/root/.cache/huggingface" \
  -e HF_HOME=/root/.cache/huggingface \
  "$IMAGE" "${ARGS[@]}"

ffmpeg -y -i "$OUTPUT" \
  -af "highpass=f=25,lowpass=f=15000,loudnorm=I=-18:TP=-1.5:LRA=9,aformat=channel_layouts=stereo" \
  -ar 48000 "${OUTPUT%.wav}.mastered.wav"

echo "Done -> ${OUTPUT%.wav}.mastered.wav"