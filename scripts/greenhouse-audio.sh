#!/bin/bash
# Generate warm botanical ambience without a continuous rain or noise bed.
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
  -f lavfi -t "$DURATION" -i "sine=frequency=523.25:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=659.25:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=783.99:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=987.77:sample_rate=48000" \
  -filter_complex "
    [0:a]volume='0.020*(0.72+0.28*sin(2*PI*t/43))':eval=frame,aformat=channel_layouts=stereo[c2];
    [1:a]volume='0.012*(0.70+0.30*sin(2*PI*t/57+0.8))':eval=frame,haas=left_delay=1.2:right_delay=7.0[g2];
    [2:a]volume='0.008*(0.68+0.32*sin(2*PI*t/71+1.7))':eval=frame,haas=left_delay=7.5:right_delay=1.0[b2];
    [3:a]volume='0.007*(0.66+0.34*sin(2*PI*t/61+2.4))':eval=frame,aformat=channel_layouts=stereo[d3];
    [4:a]volume='0.009*(0.68+0.32*sin(2*PI*t/67+3.0))':eval=frame,haas=left_delay=1.5:right_delay=8.0[e3];
    [5:a]volume='0.005*(0.64+0.36*sin(2*PI*t/79+4.2))':eval=frame,haas=left_delay=8.2:right_delay=1.4[g3];
    [c2][g2][b2][d3][e3][g3]amix=inputs=6:normalize=0,
      aecho=0.90:0.16:1180|2670:0.08|0.035,lowpass=f=3600[bed];
    [6:a]volume='0.026*(between(mod(t,37),7.0,7.18)+0.52*between(mod(t,53),31.0,31.16))':eval=frame,
      aecho=0.90:0.30:820|2210:0.18|0.07,haas=left_delay=1.2:right_delay=8.5[drop1];
    [7:a]volume='0.020*between(mod(t,47),18.0,18.16)':eval=frame,
      aecho=0.90:0.28:970|2510:0.16|0.06,haas=left_delay=8.8:right_delay=1.1[drop2];
    [8:a]volume='0.015*between(mod(t,59),42.0,42.14)':eval=frame,
      aecho=0.90:0.26:1120|2890:0.14|0.05,aformat=channel_layouts=stereo[drop3];
    [9:a]volume='0.010*between(mod(t,71),56.0,56.12)':eval=frame,
      aecho=0.90:0.24:1300|3170:0.12|0.04,haas=left_delay=1.3:right_delay=9.0[drop4];
    [bed][drop1][drop2][drop3][drop4]amix=inputs=5:normalize=0:dropout_transition=0,
      highpass=f=75,lowpass=f=8500,acompressor=threshold=0.35:ratio=1.4:attack=150:release=1400,
      volume=120,loudnorm=I=-24:TP=-3:LRA=10,
      afade=t=in:st=0:d=4,afade=t=out:st=$((DURATION - 6)):d=6[out]
  " \
  -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$OUTPUT"

echo "Done -> $OUTPUT"
