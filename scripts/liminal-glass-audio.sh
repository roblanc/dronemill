#!/bin/bash
# Generate quiet, melodic liminal ambience without a continuous noise bed.
# Usage: ./scripts/liminal-glass-audio.sh <output.wav> [duration=90]

set -euo pipefail

OUTPUT="${1:-}"
DURATION="${2:-90}"

if [ -z "$OUTPUT" ]; then
  echo "Usage: $0 <output.wav> [duration=90]" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

ffmpeg -y -nostdin \
  -f lavfi -t "$DURATION" -i "sine=frequency=293.66:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=440:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=659.25:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=739.99:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=987.77:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=880:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=659.25:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=554.37:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=493.88:sample_rate=48000" \
  -filter_complex "
    [0:a]volume='if(isnan(t),0,0.016*min(1,max(0,(t-1.5)/3)))':eval=frame,aformat=channel_layouts=stereo[d];
    [1:a]volume='if(isnan(t),0,0.010*min(1,max(0,(t-2.1)/3.4)))':eval=frame,haas=left_delay=1.8:right_delay=9.5[a];
    [2:a]volume='if(isnan(t),0,0.0065*min(1,max(0,(t-3.0)/3.8)))':eval=frame,haas=left_delay=10.2:right_delay=1.5[e];
    [3:a]volume='if(isnan(t),0,0.0075*min(1,max(0,(t-3.6)/4.2)))':eval=frame,aformat=channel_layouts=stereo[fs];
    [4:a]volume='if(isnan(t),0,0.0035*min(1,max(0,(t-17.5)/4)))':eval=frame,haas=left_delay=2.4:right_delay=11.0[b];
    [d][a][e][fs][b]amix=inputs=5:normalize=0,aecho=0.86:0.18:1450|3100:0.09|0.045,lowpass=f=4200[pad];
    [5:a]volume='if(isnan(t),0,0.055*(between(mod(t,31),4.2,4.34)+0.42*between(mod(t,31),24.1,24.22)))':eval=frame,aecho=0.88:0.38:950|2850:0.24|0.10,haas=left_delay=2.0:right_delay=10.0[n1];
    [6:a]volume='if(isnan(t),0,0.040*between(mod(t,31),8.1,8.25))':eval=frame,aecho=0.88:0.36:1100|3300:0.22|0.09,haas=left_delay=11.0:right_delay=1.8[n2];
    [7:a]volume='if(isnan(t),0,0.035*between(mod(t,31),13.4,13.56))':eval=frame,aecho=0.88:0.34:1250|3750:0.20|0.08,aformat=channel_layouts=stereo[n3];
    [8:a]volume='if(isnan(t),0,0.030*between(mod(t,31),19.3,19.47))':eval=frame,aecho=0.88:0.32:1400|4200:0.18|0.07,haas=left_delay=2.2:right_delay=12.0[n4];
    [pad][n1][n2][n3][n4]amix=inputs=5:normalize=0:dropout_transition=0,
    highpass=f=140,lowpass=f=9000,acompressor=threshold=0.40:ratio=1.5:attack=120:release=1000,
    volume=100,alimiter=limit=0.70:attack=10:release=100,
    afade=t=in:st=0:d=2.5,afade=t=out:st=$((DURATION - 5)):d=5[out]
  " \
  -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$OUTPUT"

echo "Done -> $OUTPUT"
