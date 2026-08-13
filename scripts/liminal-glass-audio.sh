#!/bin/bash
# Generate sparse pastoral liminal ambience for bright, uncanny landscapes.
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
  -f lavfi -t "$DURATION" -i "sine=frequency=146.83:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=220:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=329.63:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=369.99:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=493.88:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=880:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=1318.51:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=1975.53:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=1661.22:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "aevalsrc=0.018*sin(2*PI*(1320*t+38*t*t)):s=48000" \
  -filter_complex "
    [0:a]highpass=f=100,lowpass=f=1700,volume='if(isnan(t),0.026,if(between(mod(t,31),17,17.55),0,0.032*(0.80+0.20*sin(2*PI*t/19))))':eval=frame,haas=left_delay=3.0:right_delay=13.0[wind];
    [1:a]highpass=f=2600,lowpass=f=7200,volume='if(isnan(t),0.0025,0.0032*(0.78+0.22*sin(2*PI*t/13)))':eval=frame,haas=left_delay=15.0:right_delay=2.0[air];
    [2:a]volume='if(isnan(t),0,0.010*min(1,max(0,(t-5)/2)))':eval=frame,aformat=channel_layouts=stereo[d];
    [3:a]volume='if(isnan(t),0,0.0075*min(1,max(0,(t-5.4)/2.2)))':eval=frame,haas=left_delay=1.3:right_delay=8.7[a];
    [4:a]volume='if(isnan(t),0,0.0048*min(1,max(0,(t-6.0)/2.1)))':eval=frame,haas=left_delay=9.1:right_delay=1.6[e];
    [5:a]volume='if(isnan(t),0,0.0055*min(1,max(0,(t-6.3)/2.4)))':eval=frame,aformat=channel_layouts=stereo[fs];
    [6:a]volume='if(isnan(t),0,0.0032*min(1,max(0,(t-18)/2)))':eval=frame,haas=left_delay=2.2:right_delay=10.4[b];
    [d][a][e][fs][b]amix=inputs=5:normalize=0,lowpass=f=4800,aecho=0.82:0.22:1300|2800:0.10|0.055[pad];
    [7:a]volume='if(isnan(t),0,0.055*(between(mod(t,31),4.0,4.10)+0.55*between(mod(t,31),24.25,24.34)))':eval=frame,aecho=0.84:0.38:720|2140:0.25|0.10,haas=left_delay=2.0:right_delay=9.0[p1];
    [8:a]volume='if(isnan(t),0,0.026*between(mod(t,31),12.10,12.18))':eval=frame,aecho=0.84:0.34:930|2410:0.22|0.09,haas=left_delay=12.0:right_delay=1.5[p2];
    [9:a]volume='if(isnan(t),0,0.022*between(mod(t,31),14.85,14.93))':eval=frame,aecho=0.84:0.32:1080|2650:0.20|0.08,haas=left_delay=3.0:right_delay=14.0[p3];
    [10:a]volume='if(isnan(t),0,0.018*between(mod(t,31),16.20,16.27))':eval=frame,aecho=0.85:0.30:1210|2890:0.18|0.07,haas=left_delay=15.0:right_delay=2.0[p4];
    [11:a]highpass=f=900,lowpass=f=2700,volume='if(isnan(t),0,between(mod(t,31),9.0,9.34))':eval=frame,aecho=0.80:0.20:1650:0.12,pan=stereo|c0=0.18*c0|c1=0.55*c0[bird];
    [wind][air][pad][p1][p2][p3][p4][bird]amix=inputs=8:normalize=0:dropout_transition=0,
    highpass=f=55,lowpass=f=11500,acompressor=threshold=0.28:ratio=1.8:attack=100:release=850,
    loudnorm=I=-18:TP=-1.5:LRA=10,afade=t=in:st=0:d=2.5,afade=t=out:st=$((DURATION - 4)):d=4[out]
  " \
  -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$OUTPUT"

echo "Done -> $OUTPUT"
