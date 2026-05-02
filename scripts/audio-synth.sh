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

# Pseudo-random base frequencies derived from seed
BASE_FREQ=$((40 + (SEED % 50)))           # 40-90 Hz drone
PAD_FREQ=$((110 + (SEED % 60)))           # 110-170 Hz pad
SUB_FREQ=$((20 + (SEED % 15)))            # 20-35 Hz sub

echo ">> Synthesizing ${DUR}s ambient (seed=$SEED, base=${BASE_FREQ}Hz, pad=${PAD_FREQ}Hz)..."

# Layer 1: brown noise (base atmosphere)
# Layer 2: sine drone @ BASE_FREQ with slow LFO
# Layer 3: pad sine @ PAD_FREQ tremolo
# Layer 4: sub bass @ SUB_FREQ
# Mix + reverb-like aecho + lowpass for warmth + compression

ffmpeg -y \
  -f lavfi -t "$DUR" -i "anoisesrc=c=brown:r=44100:a=0.25" \
  -f lavfi -t "$DUR" -i "sine=frequency=${BASE_FREQ}:sample_rate=44100" \
  -f lavfi -t "$DUR" -i "sine=frequency=${PAD_FREQ}:sample_rate=44100" \
  -f lavfi -t "$DUR" -i "sine=frequency=${SUB_FREQ}:sample_rate=44100" \
  -filter_complex "
    [0:a]volume=0.6,lowpass=f=900[base];
    [1:a]volume=0.3,tremolo=f=0.08:d=0.4[drone];
    [2:a]volume=0.15,tremolo=f=0.05:d=0.6,lowpass=f=2000[pad];
    [3:a]volume=0.4[sub];
    [base][drone][pad][sub]amix=inputs=4:duration=longest:dropout_transition=0,
    aecho=0.7:0.5:1500:0.4,
    lowpass=f=4500,
    acompressor=threshold=0.3:ratio=3:attack=200:release=1000,
    volume=1.5
  " \
  -c:a libmp3lame -b:a 192k "$OUT"

echo "Done -> $OUT"
