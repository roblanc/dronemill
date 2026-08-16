#!/bin/bash
set -uo pipefail
cd /home/brewuser/projects/dronemill
mkdir -p audio/bases/batch3

gen() {
  local slug="$1"; local prompt="$2"
  echo "=== $slug ==="
  ./scripts/latentscore-gen.sh "$prompt" "audio/bases/batch3/$slug.wav" 1800 > "/tmp/ls-base-$slug.log" 2>&1 || { echo "FAIL $slug"; tail -3 "/tmp/ls-base-$slug.log"; return 1; }
  rm -f "audio/bases/batch3/$slug.mastered.wav"
  echo "$slug base done: $(ffprobe -v error -show_entries format=duration -of csv=p=0 "audio/bases/batch3/$slug.wav" 2>/dev/null)s"
}

gen asteroid-kitchen "warm hum of a small spacecraft kitchen on a long quiet voyage home, cozy enclosed warmth, soft machinery, deep space silence outside, gentle comforting ambience"
gen rewind-season "empty television studio after broadcast, analog warmth, soft CRT glow, nostalgic room-tone stillness, gentle magnetic hum"
gen indoor-stars "desert observatory at night, constellations glowing across the interior floor, vast cosmic stillness, quiet reverence, deep spacious wonder"
gen mangrove-waterlines "moonlit mangrove swamp, luminous tidal waterlines suspended between the roots, dark reflective water, slow uncanny stillness"
gen oldest-thunder "warm prehistoric rock shelter, rainy fern basin, distant peaceful thunder, ancient earthy comfort"

echo "ALL BATCH 3 BASES DONE"