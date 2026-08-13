#!/bin/bash
# Generate warm botanical ambience without noise beds or isolated transients.
# Usage: ./scripts/greenhouse-audio.sh <output.wav> [duration=90]

set -euo pipefail

OUTPUT="${1:-}"
DURATION="${2:-90}"

if [ -z "$OUTPUT" ]; then
  echo "Usage: $0 <output.wav> [duration=90]" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

ffmpeg -y -nostdin \
  -f lavfi -t "$DURATION" -i "sine=frequency=130.81:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=196.00:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=246.94:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=293.66:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=329.63:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=392.00:sample_rate=48000" \
  -filter_complex "
    [0:a]volume='if(isnan(t),0,0.020*(0.72+0.28*sin(2*PI*t/43)))':eval=frame,aformat=channel_layouts=stereo[c2];
    [1:a]volume='if(isnan(t),0,0.012*(0.70+0.30*sin(2*PI*t/57+0.8)))':eval=frame,haas=left_delay=1.2:right_delay=7.0[g2];
    [2:a]volume='if(isnan(t),0,0.008*(0.68+0.32*sin(2*PI*t/71+1.7)))':eval=frame,haas=left_delay=7.5:right_delay=1.0[b2];
    [3:a]volume='if(isnan(t),0,0.007*(0.66+0.34*sin(2*PI*t/61+2.4)))':eval=frame,aformat=channel_layouts=stereo[d3];
    [4:a]volume='if(isnan(t),0,0.009*(0.68+0.32*sin(2*PI*t/67+3.0)))':eval=frame,haas=left_delay=1.5:right_delay=8.0[e3];
    [5:a]volume='if(isnan(t),0,0.005*(0.64+0.36*sin(2*PI*t/79+4.2)))':eval=frame,haas=left_delay=8.2:right_delay=1.4[g3];
    [c2][g2][b2][d3][e3][g3]amix=inputs=6:normalize=0,
      aecho=0.90:0.16:1180|2670:0.08|0.035,lowpass=f=3600,
      highpass=f=75,lowpass=f=8500,acompressor=threshold=0.35:ratio=1.4:attack=150:release=1400,
      volume=120,loudnorm=I=-24:TP=-3:LRA=10,
      afade=t=in:st=0:d=4,afade=t=out:st=$((DURATION - 6)):d=6[out]
  " \
  -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$OUTPUT"

echo "Done -> $OUTPUT"
