#!/bin/bash
# One entry point for legal ambient sources → audio/queue/
#
# Usage:
#   ./fetch-ambient.sh freesound [count] [extra args passed to fetch-freesound.py]
#   ./fetch-ambient.sh synth [count] [duration_sec=600]
#   ./fetch-ambient.sh noise [count] [duration_sec=600] [color=brown]
#   ./fetch-ambient.sh mix <bed_a> <bed_b> <name> [vol_a] [vol_b] [duration]
#   ./fetch-ambient.sh pack [count]   # synth + noise mix per item (zero copyright)
#
# Examples:
#   ./fetch-ambient.sh freesound 5
#   ./fetch-ambient.sh freesound 3 --query "dark drone" --min-duration 120
#   ./fetch-ambient.sh synth 4 900
#   ./fetch-ambient.sh pack 3
#   ./fetch-ambient.sh mix audio/queue/a.mp3 audio/queue/b.mp3 layered_01

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source <(grep -v '^#' "$ROOT/.env" | sed '/^\s*$/d' | sed 's/^/export /')
  set +a
fi

MODE="${1:-}"
shift || true

usage() {
  echo "Usage:"
  echo "  $0 freesound [count] [fetch-freesound.py args...]"
  echo "  $0 synth [count] [duration_sec]"
  echo "  $0 noise [count] [duration_sec] [color]"
  echo "  $0 mix <bed_a> <bed_b> <name> [vol_a] [vol_b] [duration]"
  echo "  $0 pack [count]"
  exit 1
}

[ -z "$MODE" ] && usage

case "$MODE" in
  freesound)
    COUNT="${1:-3}"
    shift || true
    exec python3 "$DIR/fetch-freesound.py" -n "$COUNT" "$@"
    ;;

  synth)
    COUNT="${1:-1}"
    DUR="${2:-600}"
    QUEUE="$ROOT/audio/queue"
    mkdir -p "$QUEUE"
    for ((i = 1; i <= COUNT; i++)); do
      SEED=$((RANDOM * RANDOM))
      NAME="synth_${SEED}"
      echo "[$i/$COUNT] procedural synth seed=$SEED (${DUR}s)"
      "$DIR/audio-synth.sh" "$DUR" "$NAME" "$SEED"
      mv "$ROOT/audio/${NAME}.mp3" "$QUEUE/${NAME}.mp3"
    done
    echo "Queued $COUNT synth beds in $QUEUE"
    ;;

  noise)
    COUNT="${1:-1}"
    DUR="${2:-600}"
    COLOR="${3:-brown}"
    QUEUE="$ROOT/audio/queue"
    mkdir -p "$QUEUE"
    for ((i = 1; i <= COUNT; i++)); do
      NAME="noise_${RANDOM}"
      echo "[$i/$COUNT] noise bed color=$COLOR (${DUR}s)"
      "$DIR/noise-gen.sh" "$DUR" "$NAME" "$COLOR"
      mv "$ROOT/audio/${NAME}.mp3" "$QUEUE/${NAME}.mp3"
    done
    echo "Queued $COUNT noise beds in $QUEUE"
    ;;

  mix)
    exec "$DIR/mix-beds.sh" "$@"
    ;;

  pack)
    COUNT="${1:-1}"
    DUR=600
    QUEUE="$ROOT/audio/queue"
    mkdir -p "$QUEUE"
    for ((i = 1; i <= COUNT; i++)); do
      SEED=$((RANDOM * RANDOM))
      SYNTH="pack_synth_${SEED}"
      NOISE="pack_noise_${SEED}"
      OUT="pack_${SEED}"
      echo "[$i/$COUNT] pack: synth+noise -> $OUT"
      "$DIR/audio-synth.sh" "$DUR" "$SYNTH" "$SEED"
      "$DIR/noise-gen.sh" "$DUR" "$NOISE" brown
      "$DIR/mix-beds.sh" "$ROOT/audio/${SYNTH}.mp3" "$ROOT/audio/${NOISE}.mp3" "$OUT" 0.75 0.25 "$DUR"
      rm -f "$ROOT/audio/${SYNTH}.mp3" "$ROOT/audio/${NOISE}.mp3"
    done
    echo "Queued $COUNT pack beds in $QUEUE"
    ;;

  *)
    usage
    ;;
esac