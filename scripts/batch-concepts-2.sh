#!/bin/bash
# Batch 2: slate items 9-13. Produce 2-hour videos and schedule them on YouTube.
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

  pub="$("$DIR/scheduler.sh")"

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

build atrium atrium "you enter the atrium where daylight falls upward | architectural dread ambient | 2 hours" \
  "$SOURCE/09-atrium-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,architecture,liminal space,2 hour ambient,dreamcore,timeless ambience"

build blue-pressure blue-pressure "blue pressure | glacial macro ambient | 2 hours" \
  "$SOURCE/10-blue-pressure-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,glacier,macro,2 hour ambient,timeless ambience"

build baggage-claim baggage-claim "the baggage claim that returned summer | liminal airport ambient | 2 hours" \
  "$SOURCE/11-baggage-claim-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,liminal space,airport,2 hour ambient,dreamcore,timeless ambience"

build salt-archive salt-archive "black water beneath the salt archive | oceanic horror ambient | 2 hours" \
  "$SOURCE/12-salt-archive-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,oceanic,horror,2 hour ambient,timeless ambience"

build cloud-roots cloud-roots "you walk where the clouds grow roots | bright surreal ambient | 2 hours" \
  "$SOURCE/13-cloud-roots-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,surreal,bright,2 hour ambient,dreamcore,timeless ambience"

echo "Batch complete: all five 2h videos produced and scheduled."