#!/bin/bash
# Produce 2-hour videos for a batch of slate concepts and schedule them on YouTube.
# Each concept: Strudel music base -> scene beds (2h) -> cosmic video (2h) -> scheduled upload.

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

build ferry ferry-terminal "you returned to the ferry terminal | liminal transit ambient | 2 hours" \
  "$SOURCE/04-ferry-terminal-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,liminal space,ferry terminal,2 hour ambient,dreamcore,timeless ambience"

build video-store video-store "every ending had changed at the video store | analog nostalgia ambient | 2 hours" \
  "$SOURCE/05-video-store-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,analog nostalgia,liminal space,2 hour ambient,timeless ambience"

build gypsum gypsum-observatory "observatory beneath the gypsum dunes | desert cosmic ambient | 2 hours" \
  "$SOURCE/06-gypsum-observatory-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,desert,space ambient,2 hour ambient,timeless ambience"

build tree-ring tree-ring-boardwalk "a boardwalk that grew rings like a tree | forest liminality ambient | 2 hours" \
  "$SOURCE/07-tree-ring-boardwalk-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,forest,liminal space,2 hour ambient,timeless ambience"

build protoceratops protoceratops-hollow "warm rain over the protoceratops hollow | prehistoric cozy ambient | 2 hours" \
  "$SOURCE/08-protoceratops-hollow-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,prehistoric,cozy ambient,2 hour ambient,timeless ambience"

echo "Batch complete: all five 2h videos produced and scheduled."