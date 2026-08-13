#!/bin/bash
# Render musicbox drone ambience without the Karplus-Strong pluck layer.
# Usage: ./scripts/musicbox-no-pluck.sh <output.wav> [duration=7200]
# musicbox: Copyright 2026 Ben Askins, CC BY-SA 4.0.

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
OUTPUT="${1:-}"
DURATION="${2:-7200}"
MUSICBOX_REF="8aa47f2c9083d246f4cf3232c799599f2263b75f"
CACHE="${MUSICBOX_CACHE_DIR:-$ROOT/.cache/musicbox}"

if [ -z "$OUTPUT" ]; then
  echo "Usage: $0 <output.wav> [duration=7200]" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")" "$ROOT/.cache"
OUTPUT_DIR="$(cd "$(dirname "$OUTPUT")" && pwd)"
OUTPUT_NAME="$(basename "$OUTPUT")"
RAW_NAME="${OUTPUT_NAME%.wav}.raw.wav"

if [ ! -d "$CACHE/.git" ]; then
  git clone --filter=blob:none https://github.com/benaskins/musicbox.git "$CACHE"
fi

git -C "$CACHE" fetch origin "$MUSICBOX_REF"
git -C "$CACHE" checkout --detach "$MUSICBOX_REF"
if git -C "$CACHE" apply --check "$ROOT/tools/musicbox-no-pluck.patch"; then
  git -C "$CACHE" apply "$ROOT/tools/musicbox-no-pluck.patch"
elif ! git -C "$CACHE" apply --reverse --check "$ROOT/tools/musicbox-no-pluck.patch"; then
  echo "ERROR: musicbox no-pluck patch does not match pinned source" >&2
  exit 1
fi

docker run --rm \
  -v "$CACHE:/work" -v "$OUTPUT_DIR:/output" -w /work \
  rust:1.88-bookworm sh -c \
  "apt-get update >/dev/null && apt-get install -y --no-install-recommends libasound2-dev >/dev/null && /usr/local/cargo/bin/cargo run --release -p musicbox-cli -- --render ${DURATION}s /output/${RAW_NAME}"

ffmpeg -y -nostdin -i "$OUTPUT_DIR/$RAW_NAME" \
  -af "highpass=f=170,lowpass=f=9000,loudnorm=I=-24:TP=-3:LRA=10" \
  -ar 48000 -c:a pcm_s24le -t "$DURATION" "$OUTPUT"
rm "$OUTPUT_DIR/$RAW_NAME"

echo "Done -> $OUTPUT"
