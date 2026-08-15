#!/bin/bash
# Universal Ambience style sound engine
# Generates warm, sub-bass heavy (60%+ sub-bass), vintage-filtered ambient music.
# Usage: ./universal-sound-engine.sh <theme_name> <output.wav> [duration=60]

set -euo pipefail

THEME="${1:-forest}"
OUTPUT="${2:-/tmp/universal_sample.wav}"
DURATION="${3:-60}"

mkdir -p "$(dirname "$OUTPUT")"

# Frequencies configured for warm, peaceful, nostalgic/classical atmospheres
case "$THEME" in
  forest|fontainebleau|pastoral)
    F_SUB1="55.00"   # A1
    F_SUB2="82.41"   # E2
    F_MID1="164.81"  # E3
    F_MID2="220.00"  # A3
    F_PAD1="659.25"  # E5
    F_PAD2="739.99"  # F#5
    F_PAD3="493.88"  # B4
    BED_COLOR="pink"
    BED_FILTER="highpass=f=80,lowpass=f=950"
    ;;
  desert|gypsum|observatory)
    F_SUB1="48.99"   # G1
    F_SUB2="73.42"   # D2
    F_MID1="146.83"  # D3
    F_MID2="196.00"  # G3
    F_PAD1="587.33"  # D5
    F_PAD2="659.25"  # E5
    F_PAD3="440.00"  # A4
    BED_COLOR="brown"
    BED_FILTER="highpass=f=60,lowpass=f=750"
    ;;
  ocean|coast|tide)
    F_SUB1="43.65"   # F1
    F_SUB2="65.41"   # C2
    F_MID1="130.81"  # C3
    F_MID2="174.61"  # F3
    F_PAD1="523.25"  # C5
    F_PAD2="659.25"  # E5
    F_PAD3="392.00"  # G4
    BED_COLOR="pink"
    BED_FILTER="highpass=f=50,lowpass=f=600"
    ;;
  *)
    F_SUB1="55.00"
    F_SUB2="82.41"
    F_MID1="164.81"
    F_MID2="220.00"
    F_PAD1="659.25"
    F_PAD2="739.99"
    F_PAD3="493.88"
    BED_COLOR="pink"
    BED_FILTER="highpass=f=80,lowpass=f=950"
    ;;
esac

echo ">> Generating Universal-style ambient audio: theme=$THEME, duration=${DURATION}s..."

ffmpeg -y -nostdin \
  -f lavfi -t "$DURATION" -i "anoisesrc=c=${BED_COLOR}:r=48000:a=1:seed=7701" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${F_SUB1}:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${F_SUB2}:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${F_MID1}:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${F_MID2}:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${F_PAD1}:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${F_PAD2}:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${F_PAD3}:sample_rate=48000" \
  -filter_complex "
    [0:a]${BED_FILTER},volume='if(isnan(t),0,0.016*(0.70+0.18*sin(2*PI*t/17)+0.12*sin(2*PI*t/41+1.4)))':eval=frame,aformat=channel_layouts=stereo[nature];
    [1:a]lowpass=f=120,volume='if(isnan(t),0,0.095*(0.75+0.25*sin(2*PI*t/29)))':eval=frame,aformat=channel_layouts=stereo[sub1];
    [2:a]lowpass=f=150,volume='if(isnan(t),0,0.065*(0.70+0.30*sin(2*PI*t/37+1.1)))':eval=frame,haas=left_delay=1.2:right_delay=5.8[sub2];
    [3:a]volume='if(isnan(t),0,0.028*(0.65+0.35*sin(2*PI*t/47+2.0)))':eval=frame,haas=left_delay=6.0:right_delay=1.1[mid1];
    [4:a]volume='if(isnan(t),0,0.024*(0.68+0.32*sin(2*PI*t/53+0.8)))':eval=frame,aformat=channel_layouts=stereo[mid2];
    [5:a]volume='if(isnan(t),0,0.018*(0.55+0.45*sin(2*PI*t/23+1.7)))':eval=frame,haas=left_delay=1.0:right_delay=8.4[p1];
    [6:a]volume='if(isnan(t),0,0.016*(0.50+0.50*sin(2*PI*t/31+3.1)))':eval=frame,haas=left_delay=8.6:right_delay=1.0[p2];
    [7:a]volume='if(isnan(t),0,0.014*(0.52+0.48*sin(2*PI*t/43+0.5)))':eval=frame,aformat=channel_layouts=stereo[p3];
    [sub1][sub2]amix=inputs=2:normalize=0[sub_mix];
    [mid1][mid2]amix=inputs=2:normalize=0[mid_mix];
    [p1][p2][p3]amix=inputs=3:normalize=0,chorus=0.25:0.38:35|48:0.06|0.045:0.07|0.05:0.09|0.07,aecho=0.92:0.20:1750|4200:0.08|0.035,lowpass=f=2800[pads_reverb];
    [sub_mix][mid_mix][pads_reverb][nature]amix=inputs=4:normalize=0:dropout_transition=0,
      highpass=f=24,lowpass=f=4200,
      acompressor=threshold=0.25:ratio=1.35:attack=200:release=1800,
      loudnorm=I=-22:TP=-3:LRA=4.5,
      afade=t=in:st=0:d=4,afade=t=out:st=$((DURATION - 5)):d=5[out]
  " -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$OUTPUT"

echo "Done -> $OUTPUT"
