#!/bin/bash
# Procedural ambient audio generator. Zero copyright risk.
# Profile-driven layers: noise bed + low-frequency drones + room-specific resonances.
#
# Usage: ./audio-synth.sh <duration_seconds> <output_name> [profile=auto] [seed]
# Backward-compatible: numeric 3rd arg is treated as seed.
# Examples:
#   ./audio-synth.sh 3600 ambient_001 backrooms 42
#   ./audio-synth.sh 3600 ambient_002 harbor
#   ./audio-synth.sh 3600 ambient_003 42

set -e

DUR="${1:-3600}"
NAME="${2:-ambient}"
PROFILE="${3:-auto}"
SEED="${4:-$RANDOM}"

if [[ "$PROFILE" =~ ^[0-9]+$ ]]; then
  SEED="$PROFILE"
  PROFILE="auto"
fi

DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$DIR/audio/${NAME}.mp3"

pick_auto_profile() {
  case $((SEED % 8)) in
    0) echo "backrooms" ;;
    1) echo "mall" ;;
    2) echo "terminal" ;;
    3) echo "poolrooms" ;;
    4) echo "server" ;;
    5) echo "arctic" ;;
    6) echo "harbor" ;;
    *) echo "void" ;;
  esac
}

if [ "$PROFILE" = "auto" ]; then
  PROFILE="$(pick_auto_profile)"
fi

# Defaults. Profiles override these.
NOISE="pink"
NOISE_VOL="0.55"
HUM_LP="260"
TONIC_BASE=105
TONIC_SPAN=28
PAD1_VOL="0.18"
PAD2_VOL="0.13"
PAD3_VOL="0.10"
BELL1_VOL="0.035"
BELL2_VOL="0.025"
TREMOLO_1="0.10"
TREMOLO_2="0.11"
TREMOLO_3="0.13"
ECHO_DELAYS="1500|3000"
ECHO_DECAYS="0.45|0.25"
LOWPASS="3200"
HIGHPASS="18"
MASTER_VOL="2.0"
COMP_THRESHOLD="0.22"

case "$PROFILE" in
  backrooms|level0)
    NOISE="pink"; NOISE_VOL="0.70"; HUM_LP="180"; TONIC_BASE=58; TONIC_SPAN=8
    PAD1_VOL="0.16"; PAD2_VOL="0.10"; PAD3_VOL="0.06"; BELL1_VOL="0.018"; BELL2_VOL="0.012"
    TREMOLO_1="0.12"; TREMOLO_2="0.10"; TREMOLO_3="0.11"
    ECHO_DELAYS="900|2600"; ECHO_DECAYS="0.35|0.18"; LOWPASS="2600"; MASTER_VOL="2.1"
    ;;
  mall)
    NOISE="pink"; NOISE_VOL="0.45"; HUM_LP="520"; TONIC_BASE=92; TONIC_SPAN=18
    PAD1_VOL="0.20"; PAD2_VOL="0.17"; PAD3_VOL="0.12"; BELL1_VOL="0.030"; BELL2_VOL="0.018"
    TREMOLO_1="0.10"; TREMOLO_2="0.11"; TREMOLO_3="0.12"
    ECHO_DELAYS="2200|4200"; ECHO_DECAYS="0.38|0.22"; LOWPASS="4200"; MASTER_VOL="1.9"
    ;;
  terminal|airport|train)
    NOISE="brown"; NOISE_VOL="0.52"; HUM_LP="340"; TONIC_BASE=72; TONIC_SPAN=14
    PAD1_VOL="0.17"; PAD2_VOL="0.12"; PAD3_VOL="0.08"; BELL1_VOL="0.025"; BELL2_VOL="0.015"
    TREMOLO_1="0.10"; TREMOLO_2="0.11"; TREMOLO_3="0.12"
    ECHO_DELAYS="1800|3600"; ECHO_DECAYS="0.42|0.24"; LOWPASS="3800"; MASTER_VOL="2.0"
    ;;
  poolrooms|water)
    NOISE="white"; NOISE_VOL="0.25"; HUM_LP="900"; TONIC_BASE=84; TONIC_SPAN=20
    PAD1_VOL="0.14"; PAD2_VOL="0.12"; PAD3_VOL="0.09"; BELL1_VOL="0.050"; BELL2_VOL="0.035"
    TREMOLO_1="0.10"; TREMOLO_2="0.13"; TREMOLO_3="0.17"
    ECHO_DELAYS="1200|2400|5100"; ECHO_DECAYS="0.55|0.35|0.18"; LOWPASS="5400"; MASTER_VOL="1.8"
    ;;
  server|machine)
    NOISE="pink"; NOISE_VOL="0.75"; HUM_LP="420"; TONIC_BASE=118; TONIC_SPAN=12
    PAD1_VOL="0.12"; PAD2_VOL="0.08"; PAD3_VOL="0.05"; BELL1_VOL="0.015"; BELL2_VOL="0.010"
    TREMOLO_1="0.18"; TREMOLO_2="0.21"; TREMOLO_3="0.27"
    ECHO_DELAYS="700|1700"; ECHO_DECAYS="0.24|0.14"; LOWPASS="3000"; MASTER_VOL="2.2"
    ;;
  arctic|ice)
    NOISE="white"; NOISE_VOL="0.38"; HUM_LP="700"; TONIC_BASE=64; TONIC_SPAN=16
    PAD1_VOL="0.13"; PAD2_VOL="0.11"; PAD3_VOL="0.09"; BELL1_VOL="0.060"; BELL2_VOL="0.045"
    TREMOLO_1="0.10"; TREMOLO_2="0.11"; TREMOLO_3="0.12"
    ECHO_DELAYS="2600|5200"; ECHO_DECAYS="0.50|0.28"; LOWPASS="5000"; MASTER_VOL="1.9"
    ;;
  harbor|ocean|coastal)
    NOISE="brown"; NOISE_VOL="0.62"; HUM_LP="300"; TONIC_BASE=70; TONIC_SPAN=18
    PAD1_VOL="0.16"; PAD2_VOL="0.12"; PAD3_VOL="0.07"; BELL1_VOL="0.040"; BELL2_VOL="0.020"
    TREMOLO_1="0.10"; TREMOLO_2="0.11"; TREMOLO_3="0.15"
    ECHO_DELAYS="2000|4100"; ECHO_DECAYS="0.46|0.24"; LOWPASS="3600"; MASTER_VOL="2.0"
    ;;
  void|deep|cosmic)
    NOISE="brown"; NOISE_VOL="0.50"; HUM_LP="160"; TONIC_BASE=42; TONIC_SPAN=10
    PAD1_VOL="0.20"; PAD2_VOL="0.14"; PAD3_VOL="0.09"; BELL1_VOL="0.020"; BELL2_VOL="0.014"
    TREMOLO_1="0.10"; TREMOLO_2="0.11"; TREMOLO_3="0.12"
    ECHO_DELAYS="3000|6100"; ECHO_DECAYS="0.52|0.26"; LOWPASS="2400"; MASTER_VOL="2.3"
    ;;
  *)
    echo "WARN: unknown profile '$PROFILE'; using auto profile" >&2
    PROFILE="$(pick_auto_profile)"
    exec "$0" "$DUR" "$NAME" "$PROFILE" "$SEED"
    ;;
esac

TONIC=$((TONIC_BASE + (SEED % TONIC_SPAN)))
DOMINANT=$(awk "BEGIN {print $TONIC * 1.5}")
OCTAVE=$(awk "BEGIN {print $TONIC * 2.0}")
BELL_1=$(awk "BEGIN {print $TONIC * 6.0}")
BELL_2=$(awk "BEGIN {print $TONIC * 8.0}")

echo ">> Synthesizing ${DUR}s ${PROFILE} ambience (seed=$SEED, tonic=${TONIC}Hz)..."

ffmpeg -y -nostdin \
  -f lavfi -t "$DUR" -i "anoisesrc=c=${NOISE}:r=44100:a=0.2" \
  -f lavfi -t "$DUR" -i "sine=frequency=${TONIC}:sample_rate=44100" \
  -f lavfi -t "$DUR" -i "sine=frequency=${DOMINANT}:sample_rate=44100" \
  -f lavfi -t "$DUR" -i "sine=frequency=${OCTAVE}:sample_rate=44100" \
  -f lavfi -t "$DUR" -i "sine=frequency=${BELL_1}:sample_rate=44100" \
  -f lavfi -t "$DUR" -i "sine=frequency=${BELL_2}:sample_rate=44100" \
  -filter_complex "
    [0:a]volume=${NOISE_VOL},lowpass=f=${HUM_LP},highpass=f=${HIGHPASS}[ac_hum];
    [1:a]volume=${PAD1_VOL},tremolo=f=${TREMOLO_1}:d=0.7[pad1];
    [2:a]volume=${PAD2_VOL},tremolo=f=${TREMOLO_2}:d=0.6[pad2];
    [3:a]volume=${PAD3_VOL},tremolo=f=${TREMOLO_3}:d=0.8[pad3];
    [4:a]volume=${BELL1_VOL},tremolo=f=0.35:d=0.95[drip1];
    [5:a]volume=${BELL2_VOL},tremolo=f=0.22:d=0.95[drip2];
    [ac_hum][pad1][pad2][pad3][drip1][drip2]amix=inputs=6:duration=longest:dropout_transition=0,
    aecho=0.8:0.7:${ECHO_DELAYS}:${ECHO_DECAYS},
    lowpass=f=${LOWPASS},
    acompressor=threshold=${COMP_THRESHOLD}:ratio=4:attack=150:release=1200,
    volume=${MASTER_VOL}
  " \
  -c:a libmp3lame -b:a 192k "$OUT"

echo "Done -> $OUT"
