#!/bin/bash
# Upscale every image in images/queue/ using Real-ESRGAN (4x).
# Idempotent: skips images already marked as upscaled (filename suffix `_4x`).
# Originals are moved to images/raw_originals/ so the queue ends up with only upscales.
#
# Usage: ./upscale-queue.sh [scale=4] [model=realesrgan-x4plus]
#
# Install (macOS):
#   1. Download precompiled binary:
#      https://github.com/xinntao/Real-ESRGAN/releases
#      Get the `realesrgan-ncnn-vulkan-...-macos.zip`, unzip,
#      move `realesrgan-ncnn-vulkan` to /usr/local/bin/  (or anywhere on PATH)
#      chmod +x /usr/local/bin/realesrgan-ncnn-vulkan
#   2. Test: `realesrgan-ncnn-vulkan -h`
#
# Alternative model names: realesrgan-x4plus, realesrgan-x4plus-anime, realesr-animevideov3
# Use the default realesrgan-x4plus for cosmic horror / painterly content.

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

SCALE="${1:-4}"
MODEL="${2:-realesrgan-x4plus}"

QUEUE="$ROOT/images/queue"
ARCHIVE="$ROOT/images/raw_originals"

if ! command -v realesrgan-ncnn-vulkan > /dev/null 2>&1; then
  cat >&2 <<EOF
ERROR: realesrgan-ncnn-vulkan not found on PATH.

Install (macOS):
  1. Visit https://github.com/xinntao/Real-ESRGAN/releases
  2. Download realesrgan-ncnn-vulkan-*-macos.zip, unzip.
  3. Move the binary to /usr/local/bin/ and chmod +x it.
  4. Test with: realesrgan-ncnn-vulkan -h

Alternative (Homebrew tap, if available):
  brew install realesrgan-ncnn-vulkan
EOF
  exit 1
fi

mkdir -p "$ARCHIVE"

shopt -s nullglob
FOUND=0
PROCESSED=0
SKIPPED=0

for IMG in "$QUEUE"/*.{png,jpg,jpeg,PNG,JPG,JPEG,webp,WEBP}; do
  [ -f "$IMG" ] || continue
  FOUND=$((FOUND+1))

  BASENAME=$(basename "$IMG")
  STEM="${BASENAME%.*}"
  EXT="${BASENAME##*.}"

  # Skip if already upscaled
  if [[ "$STEM" == *_4x ]] || [[ "$STEM" == *_${SCALE}x ]]; then
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  OUT_NAME="${STEM}_${SCALE}x.png"
  OUT_PATH="$QUEUE/$OUT_NAME"

  if [ -f "$OUT_PATH" ]; then
    echo ">> Already upscaled: $OUT_NAME (skipping)"
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  echo ">> Upscaling [$((PROCESSED+1))]: $BASENAME -> $OUT_NAME (scale=${SCALE}x, model=$MODEL)"
  realesrgan-ncnn-vulkan -i "$IMG" -o "$OUT_PATH" -s "$SCALE" -n "$MODEL" > /dev/null 2>&1

  if [ -f "$OUT_PATH" ]; then
    mv "$IMG" "$ARCHIVE/"
    PROCESSED=$((PROCESSED+1))
  else
    echo "  !! upscale failed for $BASENAME — leaving original in queue" >&2
  fi
done

echo "----------------------------------------"
echo "Queue scanned: $FOUND files"
echo "Upscaled:      $PROCESSED"
echo "Skipped:       $SKIPPED"
echo "Originals archived to: $ARCHIVE"
