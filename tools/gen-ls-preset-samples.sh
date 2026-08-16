#!/bin/bash
# Render 2-minute samples of all 12 LatentScore demo presets (natural configs).
# Renders under $ROOT (docker mounts it), then moves mp3s to /DATA/Media.
set -uo pipefail
cd /home/brewuser/projects/dronemill

WORK="/home/brewuser/projects/dronemill/audio/previews/presets"
OUT="/DATA/Media/DroneMill LatentScore Presets"
mkdir -p "$WORK" "$OUT"

render_one() {
  local id="$1"
  local wav="$WORK/$id-120s.wav"
  local mp3="$WORK/$id-120s.mp3"
  echo "=== $id ==="
  ./scripts/latentscore-gen.sh --preset "$id" "$wav" 120 --natural > /tmp/ls-$id.log 2>&1 || { echo "FAIL $id"; return 1; }
  ffmpeg -y -i "${wav%.wav}.mastered.wav" -c:a libmp3lame -q:a 2 "$mp3" 2>/dev/null || { echo "MP3FAIL $id"; return 1; }
  mv "$mp3" "$OUT/"
  local len
  len=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/$id-120s.mp3")
  echo "$id -> $OUT/$id-120s.mp3 ($len s)"
  rm -f "$wav" "${wav%.wav}.mastered.wav" "$WORK/$id-120s.json"
}

render_one deep-ocean
render_one frozen-memory
render_one zen-garden
render_one deep-space
render_one midnight-rain
render_one respect-mystery
render_one treasured-object
render_one bittersweetness
render_one stars-and-shore
render_one final-thanks
render_one healing-music
render_one neon-city

echo "ALL 12 PRESET SAMPLES DONE"
ls -la "$OUT"