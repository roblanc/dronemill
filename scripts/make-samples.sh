#!/bin/bash
# Themed ~90s audio previews for auditioning (same processing as cosmic.sh audio chain).
# Output: audio/samples/<slug>.mp3 + samples_manifest.json
#
# Usage:
#   ./make-samples.sh [pitch] [duration_sec]     # all themes (skip existing unless FORCE=1)
#   FORCE=1 ./make-samples.sh                     # rebuild everything
#   ONLY=17_office_night,18_hospital ./make-samples.sh

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"

PITCH="${1:-0.93}"
PREVIEW_SEC="${2:-90}"
RAW_DIR="$ROOT/audio/samples/raw"
OUT_DIR="$ROOT/audio/samples"
mkdir -p "$RAW_DIR" "$OUT_DIR"

if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source <(grep -v '^#' "$ROOT/.env" | sed '/^\s*$/d' | sed 's/^/export /')
  set +a
  LOUDNORM_AF="loudnorm=I=${LOUDNORM_I}:TP=${LOUDNORM_TP}:LRA=${LOUDNORM_LRA}"
fi

# slug|freesound query
THEMES=(
  "01_empty_mall|empty mall escalator room tone"
  "02_airport_terminal|empty airport terminal ambience quiet"
  "03_laundromat|laundromat washing machine hum ambient"
  "04_poolrooms|indoor swimming pool drip echo ambience"
  "05_infinite_hotel|hotel corridor night room tone empty"
  "06_library|empty library room tone quiet"
  "07_train_station|train station platform ambient distant"
  "08_suburban_night|suburban night crickets distant hum"
  "09_classroom|empty classroom room tone"
  "10_playplace|indoor playground empty ambience"
  "11_parking_garage|underground parking garage hum"
  "12_cosmic_horror|cosmic horror deep drone dark ambient"
  "16_escalator|escalator mechanical hum room tone"
  "17_office_night|empty office night fluorescent hum room tone"
  "18_hospital_corridor|hospital corridor ambience quiet distant"
  "19_supermarket_closed|empty supermarket ambience hum quiet"
  "20_metro_tunnel|subway tunnel"
  "21_elevator_shaft|elevator hum mechanical"
  "22_rain_window|rain window interior"
  "23_server_room|server room ambience"
  "24_museum_hall|museum hall reverb"
  "25_church_empty|church cathedral ambience"
  "26_backrooms|fluorescent hum drone liminal"
  "27_wind_desolate|wind desolate landscape"
  "28_aquarium|aquarium pump water"
  "29_humid_bathroom|bathroom vent fan"
  "30_void_deep|deep space drone ambient"
  "33_hotel_lobby|hotel lobby ambience"
  "34_cave_drip|cave drip echo water"
  "35_night_drive|car interior driving highway"
)

SYNTH_SEEDS=(
  "13_synth_warm|42"
  "14_synth_cold|137"
  "15_synth_dread|666"
  "31_synth_void|777"
  "32_synth_pulse|999"
  "36_synth_haze|1234"
  "37_synth_ethereal|2048"
)

should_process() {
  local slug="$1"
  if [ -n "$ONLY" ]; then
    echo ",$ONLY," | grep -q ",${slug}," || return 1
  fi
  if [ "${FORCE:-0}" = "1" ]; then
    return 0
  fi
  [ ! -f "$OUT_DIR/${slug}.mp3" ]
}

process_preview() {
  local in="$1"
  local out="$2"
  local sr
  sr=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=noprint_wrappers=1:nokey=1 "$in")
  [ -z "$sr" ] || ! [[ "$sr" =~ ^[0-9]+$ ]] && sr=44100

  ffmpeg -y -nostdin -stream_loop -1 -i "$in" \
    -af "asetrate=${sr}*${PITCH},aresample=${sr},atempo=$(awk "BEGIN {print 1/${PITCH}}"),lowpass=f=8000,${LOUDNORM_AF}" \
    -t "$PREVIEW_SEC" -c:a libmp3lame -b:a 192k "$out" 2>/dev/null
}

resolve_raw() {
  local slug="$1"
  local raw="$RAW_DIR/${slug}.mp3"
  if [ -f "$raw" ]; then
    echo "$raw"
    return 0
  fi
  return 1
}

fetch_raw() {
  local slug="$1"
  local query="$2"
  local raw="$RAW_DIR/${slug}.mp3"

  echo "[$slug] fetching: $query"
  local fetch_ok=0
  for lic in cc0 by; do
    if python3 "$DIR/fetch-freesound.py" -n 1 --sequential -q "$query" \
        --license "$lic" --min-duration 10 --max-duration 300 --sort duration_asc -o "$RAW_DIR"; then
      fetch_ok=1
      break
    fi
    echo "  retry with license=$lic failed, trying next..." >&2
  done
  if [ "$fetch_ok" -ne 1 ]; then
    echo "  WARN: fetch failed" >&2
    return 1
  fi
  local fetched
  fetched=$(ls -t "$RAW_DIR"/fs*.mp3 2>/dev/null | head -1)
  if [ -n "$fetched" ] && [ "$fetched" != "$raw" ]; then
    mv -f "$fetched" "$raw"
  fi
  [ -f "$raw" ]
}

echo ">> Themed samples -> $OUT_DIR (${PREVIEW_SEC}s, pitch=$PITCH, loudnorm ${LOUDNORM_I} LUFS)"
[ -n "$ONLY" ] && echo ">> ONLY=$ONLY"
[ "${FORCE:-0}" = "1" ] && echo ">> FORCE rebuild"
echo ""

built=0
skipped=0

for entry in "${THEMES[@]}"; do
  slug="${entry%%|*}"
  query="${entry#*|}"
  out="$OUT_DIR/${slug}.mp3"

  if ! should_process "$slug"; then
    echo "[$slug] skip (exists)"
    skipped=$((skipped + 1))
    continue
  fi

  raw=$(resolve_raw "$slug" || true)
  if [ -z "$raw" ]; then
    fetch_raw "$slug" "$query" || continue
    raw="$RAW_DIR/${slug}.mp3"
  fi

  echo "[$slug] rendering..."
  process_preview "$raw" "$out"
  echo "  -> $out"
  built=$((built + 1))
done

for entry in "${SYNTH_SEEDS[@]}"; do
  slug="${entry%%|*}"
  seed="${entry#*|}"
  out="$OUT_DIR/${slug}.mp3"
  tmp="$ROOT/audio/_sample_${slug}.mp3"

  if ! should_process "$slug"; then
    echo "[$slug] skip (exists)"
    skipped=$((skipped + 1))
    continue
  fi

  echo "[$slug] procedural synth seed=$seed"
  "$DIR/audio-synth.sh" "$PREVIEW_SEC" "_sample_${slug}" "$seed" 2>/dev/null
  process_preview "$tmp" "$out"
  rm -f "$tmp"
  echo "  -> $out"
  built=$((built + 1))
done

python3 - "$OUT_DIR" <<'PY'
import json, sys
from pathlib import Path

out_dir = Path(sys.argv[1])
labels = {
    "01_empty_mall": ("Empty mall / scări", "Freesound"),
    "02_airport_terminal": ("Airport terminal gol", "Freesound"),
    "03_laundromat": ("Laundromat / uscător", "Freesound"),
    "04_poolrooms": ("Pool rooms / piscină interioară", "Freesound"),
    "05_infinite_hotel": ("Infinite hotel / cabină", "Freesound"),
    "06_library": ("Library / sală liniștită", "Freesound"),
    "07_train_station": ("Train station / gară", "Freesound"),
    "08_suburban_night": ("Suburban night / noapte suburbie", "Freesound"),
    "09_classroom": ("Classroom / birou gol", "Freesound"),
    "10_playplace": ("Playplace / sală goală reverb", "Freesound"),
    "11_parking_garage": ("Parking garage / subsol", "Freesound"),
    "12_cosmic_horror": ("Cosmic horror / submarin", "Freesound"),
    "13_synth_warm": ("Synth warm drone", "Procedural"),
    "14_synth_cold": ("Synth cold drone", "Procedural"),
    "15_synth_dread": ("Synth dread drone", "Procedural"),
    "16_escalator": ("Escalator / hum mecanic", "Freesound"),
    "17_office_night": ("Office night / birou noapte", "Freesound"),
    "18_hospital_corridor": ("Hospital corridor / spital", "Freesound"),
    "19_supermarket_closed": ("Supermarket închis", "Freesound"),
    "20_metro_tunnel": ("Metro tunnel / metrou", "Freesound"),
    "21_elevator_shaft": ("Elevator shaft / lift", "Freesound"),
    "22_rain_window": ("Rain on window / ploaie", "Freesound"),
    "23_server_room": ("Server room / datacenter", "Freesound"),
    "24_museum_hall": ("Museum hall / muzeu gol", "Freesound"),
    "25_church_empty": ("Church empty / biserică", "Freesound"),
    "26_backrooms": ("Backrooms / liminal fluorescent", "Freesound"),
    "27_wind_desolate": ("Wind desolate / vânt pustiu", "Freesound"),
    "28_aquarium": ("Aquarium / acvariu pump", "Freesound"),
    "29_humid_bathroom": ("Bathroom vent / baie ventilator", "Freesound"),
    "30_void_deep": ("Void deep / spațiu profund", "Freesound"),
    "31_synth_void": ("Synth void drone", "Procedural"),
    "32_synth_pulse": ("Synth pulse drone", "Procedural"),
    "33_hotel_lobby": ("Hotel lobby / hol hotel gol", "Freesound"),
    "34_cave_drip": ("Cave drip / peșteră picături", "Freesound"),
    "35_night_drive": ("Night drive / drum noapte", "Freesound"),
    "36_synth_haze": ("Synth haze drone", "Procedural"),
    "37_synth_ethereal": ("Synth ethereal drone", "Procedural"),
}

entries = []
for mp3 in sorted(out_dir.glob("*.mp3")):
    slug = mp3.stem
    theme, source = labels.get(slug, (slug.replace("_", " "), "Unknown"))
    entries.append({
        "file": mp3.name,
        "slug": slug,
        "theme": theme,
        "source": source,
        "lufs_target": -18,
    })

manifest = out_dir / "samples_manifest.json"
manifest.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")
print(f"Manifest: {manifest} ({len(entries)} entries)")
PY

count=$(find "$OUT_DIR" -maxdepth 1 -name '*.mp3' -type f | wc -l | xargs)
echo ""
echo "Done: built=$built skipped=$skipped total=$count in $OUT_DIR"