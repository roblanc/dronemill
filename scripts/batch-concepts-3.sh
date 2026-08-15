#!/bin/bash
# Batch 3: slate items 14-18. LatentScore music bases -> 2-hour videos, scheduled on YouTube.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"

MEDIA="${DRONEMILL_MEDIA_DIR:-/DATA/Media}"
SOURCE="/DATA/Media/DroneMill ChatGPT Concepts"
BASSES="$ROOT/audio/bases/batch3"
DURATION=7200

build() {
  local mode="$1" slug="$2" title="$3" image="$4" tags="$5"
  local base="$BASSES/$slug.wav"
  local work="${TMPDIR:-/tmp}/dronemill-$slug-prod-$$"
  local mix="$work/mix.wav"
  local video="$MEDIA/$(slugify "$title").mp4"
  local desc="$ROOT/descriptions/$slug-2h.txt"
  local pub

  pub="$("$DIR/scheduler.sh")"

  mkdir -p "$work"
  echo "=== $title ==="
  echo "[1/4] LatentScore base (30min continuous, single chord)"
  if [ ! -f "$base" ]; then echo "MISSING base $base"; return 1; fi
  echo "     base: $base ($(ffprobe -v error -show_entries format=duration -of csv=p=0 "$base")s)"
  echo "[2/4] 2h scene mix ($mode beds + music)"
  "$DIR/lighthouse-style-scene-audio.sh" "$mode" "$base" "$mix" "$DURATION"
  echo "[3/4] 2h video"
  "$DIR/cosmic.sh" "$mix" "$image" "$title" 1.0 "$DURATION"
  echo "[4/4] Upload to YouTube (scheduled for $pub UTC)"
  "$DIR/upload-yt.sh" "$video" "$title" "$desc" "$image" private "$tags" "$pub"
  rm -f "$mix"
  rm -rf "$work"
}

build asteroid-kitchen asteroid-kitchen "a kitchen drifting through the asteroid winter | cozy sci-fi ambient | 2 hours" \
  "$SOURCE/14-asteroid-kitchen-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,sci-fi,space,cozy,2 hour ambient,timeless ambience"

build rewind-season rewind-season "rewind season | analog broadcast ambient | 2 hours" \
  "$SOURCE/15-rewind-season-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,analog,nostalgia,2 hour ambient,dreamcore,timeless ambience"

build indoor-stars indoor-stars "you reached the observatory, but the stars had gone indoors | desert cosmic ambient | 2 hours" \
  "$SOURCE/16-indoor-stars-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,observatory,space,cosmic,2 hour ambient,timeless ambience"

build mangrove-waterlines mangrove-waterlines "moonlit waterlines in the mangrove forest | swamp dark ambient | 2 hours" \
  "$SOURCE/17-mangrove-waterlines-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,swamp,moonlit,water,2 hour ambient,timeless ambience"

build oldest-thunder oldest-thunder "you rest beneath the oldest thunder | prehistoric refuge ambient | 2 hours" \
  "$SOURCE/18-oldest-thunder-chatgpt.png" \
  "ambient,cosmic horror,dark ambient,sleep music,study music,prehistoric,rain,earth,2 hour ambient,timeless ambience"

echo "Batch complete: all five 2h videos produced and scheduled."