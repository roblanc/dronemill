#!/bin/bash
set -uo pipefail
cd /home/brewuser/projects/dronemill
ROOT="$(pwd)"
mkdir -p audio/bases/batch3 .tmp-b3-chunks

gen() {
  local slug="$1"; local prompt="$2"
  echo "=== $slug ==="
  local work="$ROOT/.tmp-b3-chunks/$slug"
  mkdir -p "$work"
  local ok=1
  for i in 1 2 3; do
    echo "  chunk $i/3 ..."
    ./scripts/latentscore-gen.sh "$prompt" "$work/c$i.wav" 600 > "$work/c$i.log" 2>&1 \
      || { echo "FAIL chunk $i"; tail -3 "$work/c$i.log"; ok=0; break; }
    rm -f "$work/c$i.mastered.wav"
  done
  if [ "$ok" = 1 ]; then
    ffmpeg -y -nostdin \
      -i "$work/c1.wav" -i "$work/c2.wav" -i "$work/c3.wav" \
      -filter_complex "[0:a]aformat=sample_fmts=s16:channel_layouts=mono[a0];[1:a]aformat=sample_fmts=s16:channel_layouts=mono[a1];[2:a]aformat=sample_fmts=s16:channel_layouts=mono[a2];[a0][a1]acrossfade=d=8[a01];[a01][a2]acrossfade=d=8[out]" \
      -map "[out]" -ar 44100 "audio/bases/batch3/$slug.wav" > "$work/final.log" 2>&1 \
      || { echo "FAIL crossfade"; tail -3 "$work/final.log"; ok=0; }
  fi
  if [ "$ok" = 1 ]; then
    echo "$slug base done: $(ffprobe -v error -show_entries format=duration -of csv=p=0 "audio/bases/batch3/$slug.wav")s"
  fi
  rm -rf "$work"
}

gen asteroid-kitchen "warm hum of a small spacecraft kitchen on a long quiet voyage home, cozy enclosed warmth, soft machinery, deep space silence outside, gentle comforting ambience"
gen rewind-season "empty television studio after broadcast, analog warmth, soft CRT glow, nostalgic room-tone stillness, gentle magnetic hum"
gen indoor-stars "desert observatory at night, constellations glowing across the interior floor, vast cosmic stillness, quiet reverence, deep spacious wonder"
gen mangrove-waterlines "moonlit mangrove swamp, luminous tidal waterlines suspended between the roots, dark reflective water, slow uncanny stillness"
gen oldest-thunder "warm prehistoric rock shelter, rainy fern basin, distant peaceful thunder, ancient earthy comfort"

echo "ALL BATCH 3 BASES DONE"