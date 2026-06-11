#!/bin/bash
# Re-render audio/samples/*.mp3 at current LOUDNORM_* (no Freesound fetch).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"
PITCH="${1:-0.93}"
PREVIEW_SEC="${2:-90}"
OUT="$ROOT/audio/samples"

process_preview() {
  local in="$1" out="$2" sr
  sr=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=noprint_wrappers=1:nokey=1 "$in")
  [ -z "$sr" ] || ! [[ "$sr" =~ ^[0-9]+$ ]] && sr=44100
  ffmpeg -y -nostdin -stream_loop -1 -i "$in" \
    -af "asetrate=${sr}*${PITCH},aresample=${sr},atempo=$(awk "BEGIN {print 1/${PITCH}}"),lowpass=f=8000,${LOUDNORM_AF}" \
    -t "$PREVIEW_SEC" -c:a libmp3lame -b:a 192k "$out" 2>/dev/null
}

pairs=(
  "01_empty_mall|$ROOT/audio/used/fs387341-room-tone-stairs-wav.mp3"
  "02_airport_terminal|$ROOT/audio/queue/fs801939-some-airy-reverberation-ambience.mp3"
  "03_laundromat|$ROOT/audio/samples/raw/fs845418-tumble-dryer-consistent-mechanical-hum-and-rotating-drum.mp3"
  "04_poolrooms|$ROOT/audio/samples/raw/fs527200-2020-06-27-swimming-pool.mp3"
  "05_infinite_hotel|$ROOT/audio/queue/fs806017-cruise-ship-cabin-room-tone.mp3"
  "06_library|$ROOT/audio/samples/raw/06_library.mp3"
  "07_train_station|$ROOT/audio/samples/raw/07_train_station.mp3"
  "08_suburban_night|$ROOT/audio/samples/raw/08_suburban_night.mp3"
  "09_classroom|$ROOT/audio/samples/raw/fs609250-journey-to-the-interweb.mp3"
  "10_playplace|$ROOT/audio/samples/raw/fs613738-amb-ost1-mp3.mp3"
  "11_parking_garage|$ROOT/audio/samples/raw/fs803970-abandoned-basement-drone.mp3"
  "12_cosmic_horror|$ROOT/audio/samples/raw/12_cosmic_horror.mp3"
  "16_escalator|$ROOT/audio/samples/raw/fs586898-mechanical-hum.mp3"
)

echo ">> Remaster samples at ${LOUDNORM_I} LUFS (${PREVIEW_SEC}s)"
for pair in "${pairs[@]}"; do
  slug="${pair%%|*}"
  src="${pair#*|}"
  out="$OUT/${slug}.mp3"
  [ -f "$src" ] || { echo "SKIP $slug (missing $src)" >&2; continue; }
  echo "[$slug]"
  process_preview "$src" "$out"
done

for entry in "13_synth_warm|42" "14_synth_cold|137" "15_synth_dread|666"; do
  slug="${entry%%|*}"
  seed="${entry#*|}"
  out="$OUT/${slug}.mp3"
  tmp="$ROOT/audio/_sample_${slug}.mp3"
  echo "[$slug] synth seed=$seed"
  "$DIR/audio-synth.sh" "$PREVIEW_SEC" "_sample_${slug}" "$seed" >/dev/null
  process_preview "$tmp" "$out"
  rm -f "$tmp"
done

echo "Done."