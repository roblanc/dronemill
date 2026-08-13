#!/bin/bash
# Generate airy ambience with sparse glass resonances for liminal landscapes.
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
  -f lavfi -t "$DURATION" -i "anoisesrc=c=pink:r=48000:a=1" \
  -f lavfi -t "$DURATION" -i "anoisesrc=c=white:r=48000:a=1" \
  -f lavfi -t "$DURATION" -i "sine=frequency=110:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=165:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=1318.51:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=1760:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=2637.02:sample_rate=48000" \
  -filter_complex "
    [0:a]highpass=f=90,lowpass=f=1250,volume='if(isnan(t),0.043,0.055*(0.78+0.22*sin(2*PI*t/17)))':eval=frame,aformat=channel_layouts=stereo[air];
    [1:a]highpass=f=1800,lowpass=f=6200,volume='if(isnan(t),0.009,0.012*(0.72+0.28*sin(2*PI*t/11)))':eval=frame,haas=left_delay=3.2:right_delay=15.8[shimmer];
    [2:a]volume='if(isnan(t),0.025,0.035*(0.72+0.28*sin(2*PI*t/23)))':eval=frame,aformat=channel_layouts=stereo[tonic];
    [3:a]volume='if(isnan(t),0.016,0.022*(0.74+0.26*sin(2*PI*t/29)))':eval=frame,haas=left_delay=1.7:right_delay=12.4[fifth];
    [4:a]volume='if(isnan(t),0,0.045*(between(mod(t,19),3.0,3.16)+between(mod(t,29),17.0,17.13)))':eval=frame,afade=t=in:st=3:d=0.035,aecho=0.82:0.42:760|1510:0.28|0.14,aformat=channel_layouts=stereo[g1];
    [5:a]volume='if(isnan(t),0,0.032*(between(mod(t,23),9.0,9.12)+between(mod(t,31),24.0,24.14)))':eval=frame,aecho=0.84:0.38:980|1960:0.24|0.11,haas=left_delay=10.8:right_delay=2.6[g2];
    [6:a]volume='if(isnan(t),0,0.022*(between(mod(t,37),14.0,14.10)+between(mod(t,41),33.0,33.11)))':eval=frame,aecho=0.86:0.34:1250|2500:0.22|0.09,aformat=channel_layouts=stereo[g3];
    [air][shimmer][tonic][fifth][g1][g2][g3]amix=inputs=7:normalize=0:dropout_transition=0,
    highpass=f=35,lowpass=f=12500,acompressor=threshold=0.24:ratio=2:attack=80:release=700,
    loudnorm=I=-18:TP=-1.5:LRA=8,afade=t=in:st=0:d=2.5,afade=t=out:st=$((DURATION - 4)):d=4[out]
  " \
  -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$OUTPUT"

echo "Done -> $OUTPUT"
