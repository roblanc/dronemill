#!/bin/bash
# Procedural cosmic horror ambient audio generator. Zero copyright risk.
# Layers: brown noise base + low-freq drone + filtered sine pad + occasional reverb hits.
#
# Usage: ./audio-synth.sh <duration_seconds> <output_name> [seed]
# Example: ./audio-synth.sh 3600 ambient_001 42

set -e

DUR="${1:-3600}"
NAME="${2:-ambient}"
SEED="${3:-$RANDOM}"

DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$DIR/audio/${NAME}.mp3"

# Calculate note frequencies based on seed (dynamic but harmonious)
TONIC=$((110 + (SEED % 20)))            # ~110-130 Hz tonic (warm room resonance)
DOMINANT=$(awk "BEGIN {print $TONIC * 1.5}") # Perfect 5th chord note
OCTAVE=$(awk "BEGIN {print $TONIC * 2.0}")   # Octave chord note
BELL_1=$(awk "BEGIN {print $TONIC * 6.0}")   # High resonant ping 1 (~660-780 Hz)
BELL_2=$(awk "BEGIN {print $TONIC * 8.0}")   # High resonant ping 2 (~880-1040 Hz)

echo ">> Synthesizing ${DUR}s liminal ambience (seed=$SEED, tonic=${TONIC}Hz)..."

ffmpeg -y -nostdin \
  -f lavfi -t "$DUR" -i "anoisesrc=c=pink:r=44100:a=0.2" \
  -f lavfi -t "$DUR" -i "sine=frequency=${TONIC}:sample_rate=44100" \
  -f lavfi -t "$DUR" -i "sine=frequency=${DOMINANT}:sample_rate=44100" \
  -f lavfi -t "$DUR" -i "sine=frequency=${OCTAVE}:sample_rate=44100" \
  -f lavfi -t "$DUR" -i "sine=frequency=${BELL_1}:sample_rate=44100" \
  -f lavfi -t "$DUR" -i "sine=frequency=${BELL_2}:sample_rate=44100" \
  -filter_complex "
    [0:a]volume=0.6,lowpass=f=250[ac_hum];
    [1:a]volume=0.2,tremolo=f=0.1:d=0.7[pad1];
    [2:a]volume=0.15,tremolo=f=0.12:d=0.6[pad2];
    [3:a]volume=0.15,tremolo=f=0.14:d=0.8[pad3];
    [4:a]volume=0.06,tremolo=f=0.35:d=0.95[drip1];
    [5:a]volume=0.04,tremolo=f=0.22:d=0.95[drip2];
    [ac_hum][pad1][pad2][pad3][drip1][drip2]amix=inputs=6:duration=longest:dropout_transition=0,
    aecho=0.8:0.7:1500|3000:0.5|0.3,
    lowpass=f=3000,
    acompressor=threshold=0.2:ratio=4:attack=150:release=1200,
    volume=2.2
  " \
  -c:a libmp3lame -b:a 192k "$OUT"

echo "Done -> $OUT"
