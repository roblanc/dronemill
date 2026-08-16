#!/bin/bash
# Render 2-minute dark ambient samples (no lead, low register) of the DroneMill themed variations.
set -uo pipefail
cd /home/brewuser/projects/dronemill

WORK="/home/brewuser/projects/dronemill/audio/previews/presets"
OUT="/DATA/Media/DroneMill LatentScore Presets"
mkdir -p "$WORK" "$OUT"

render_one() {
  local id="$1"
  local wav="$WORK/$id-dark.wav"
  local mp3="$WORK/$id-dark.mp3"
  echo "=== $id (dark, no high) ==="
  ./scripts/latentscore-gen.sh --preset "$id" "$wav" 120 > /tmp/ls-$id-dark.log 2>&1 || { echo "FAIL $id"; return 1; }
  ffmpeg -y -i "${wav%.wav}.mastered.wav" -c:a libmp3lame -q:a 2 "$mp3" 2>/dev/null || { echo "MP3FAIL $id"; return 1; }
  mv "$mp3" "$OUT/$id-dark-120s.mp3"
  local len
  len=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/$id-dark-120s.mp3")
  echo "$id -> $OUT/$id-dark-120s.mp3 ($len s)"
  rm -f "$wav" "${wav%.wav}.mastered.wav" "$WORK/$id-dark.json"
}

render_one liminal-corridor
render_one drowned-lighthouse
render_one fern-valley-rain
render_one black-tide-circle
render_one voyage-home-kitchen

echo "ALL 5 DARK VARIATIONS DONE"
ls -la "$OUT" | grep -E "dark-120s"