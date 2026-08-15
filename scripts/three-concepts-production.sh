#!/bin/bash
# Produce 2-hour production videos for the three approved concepts and upload to YouTube.
# Each concept: Strudel music base -> mode-specific scene beds (2h) -> cosmic video (2h) -> upload.

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"

STRUDEL_ROOT="${STRUDEL_MUSIC_ROOT:-/root/.claude/skills/strudel-music}"
MEDIA="${DRONEMILL_MEDIA_DIR:-/DATA/Media}"
SOURCE="/DATA/Media/DroneMill ChatGPT Concepts"
DURATION=7200
BASE_SECONDS=1800
BASE_CYCLES=450

build() {
  local mode="$1" slug="$2" title="$3" image="$4" tags="$5"
  local work="${TMPDIR:-/tmp}/dronemill-$slug-prod-$$"
  local comp="$ROOT/assets/compositions/$slug-v5.js"
  local base="$work/base.wav"
  local mix="$work/mix.wav"
  local video="$MEDIA/$(slugify "$title").mp4"
  local desc="$ROOT/descriptions/$slug-2h.txt"
  local pub

  pub="$("$DIR/scheduler.sh")"   # next day after the last scheduled slot

  mkdir -p "$work"
  echo "=== $title ==="
  echo "[1/4] Strudel base (${BASE_SECONDS}s unique music)"
  node "$STRUDEL_ROOT/src/runtime/chunked-render.mjs" "$comp" "$base" "$BASE_CYCLES" 60
  echo "[2/4] 2h scene mix ($mode beds + music)"
  "$DIR/lighthouse-style-scene-audio.sh" "$mode" "$base" "$mix" "$DURATION"
  echo "[3/4] 2h video"
  "$DIR/cosmic.sh" "$mix" "$image" "$title" 1.0 "$DURATION"
  echo "[4/4] Upload to YouTube (scheduled for $pub UTC)"
  "$DIR/upload-yt.sh" "$video" "$title" "$desc" "$image" private "$tags" "$pub"
  rm -f "$mix" "$base"
  rm -rf "$work"
}

build noonbloom noonbloom "translucent fields at noon | alien desert dark ambient | 2 hours" \
  "$SOURCE/01-noonbloom-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,alien desert,2 hour ambient,ethereal ambient,timeless ambience"

build tide tide-climbed-sky "the tide that climbed into the sky | anti-cosmic ocean ambient | 2 hours" \
  "$SOURCE/02-the-tide-that-climbed-into-the-sky-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,ocean ambient,anti-cosmic,2 hour ambient,timeless ambience"

build ceramics orbital-ceramics "orbital ceramics workshop | deep space warm ambient | 2 hours" \
  "$SOURCE/03-orbital-ceramics-workshop-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,deep space,2 hour ambient,scifi ambient,timeless ambience"

echo "All three 2h concept videos produced and uploaded."