#!/bin/bash
# Render foreground ambient music over subdued scene-authored environmental beds.
# Usage: ./scripts/scene-sound-v2.sh <noonbloom|tide|ceramics> <output.wav> [duration=120]

set -euo pipefail

MODE="${1:-}"
OUTPUT="${2:-}"
DURATION="${3:-120}"

if [ -z "$OUTPUT" ]; then
  echo "Usage: $0 <noonbloom|tide|ceramics> <output.wav> [duration=120]" >&2
  exit 2
fi

mkdir -p "$(dirname "$OUTPUT")"

case "$MODE" in
  noonbloom)
    # A deliberately voiced, slowly breathing Lydian field leads the mix. Wind
    # and membrane texture provide quiet environmental depth behind the music.
    ffmpeg -y -nostdin \
      -f lavfi -t "$DURATION" -i "anoisesrc=c=brown:r=48000:a=1:seed=1103" \
      -f lavfi -t "$DURATION" -i "anoisesrc=c=pink:r=48000:a=1:seed=1109" \
      -f lavfi -t "$DURATION" -i "anoisesrc=c=white:r=48000:a=1:seed=1117" \
      -f lavfi -t "$DURATION" -i "anoisesrc=c=pink:r=48000:a=1:seed=1123" \
      -f lavfi -t "$DURATION" -i "sine=frequency=146.83:sample_rate=48000" \
      -f lavfi -t "$DURATION" -i "sine=frequency=220.00:sample_rate=48000" \
      -f lavfi -t "$DURATION" -i "sine=frequency=277.18:sample_rate=48000" \
      -f lavfi -t "$DURATION" -i "sine=frequency=329.63:sample_rate=48000" \
      -f lavfi -t "$DURATION" -i "sine=frequency=415.30:sample_rate=48000" \
      -filter_complex "
        [0:a]lowpass=f=210,volume='if(isnan(t),0,0.022*(0.72+0.18*sin(2*PI*t/29)+0.10*sin(2*PI*t/71+1.2)))':eval=frame,aformat=channel_layouts=stereo[ground];
        [1:a]highpass=f=95,lowpass=f=1450,volume='if(isnan(t),0,0.026*(0.62+0.23*sin(2*PI*t/17+0.4)+0.15*sin(2*PI*t/43+2.1)))':eval=frame,haas=left_delay=1.1:right_delay=6.4[windbody];
        [2:a]highpass=f=650,lowpass=f=5200,volume='if(isnan(t),0,0.008*(0.70+0.18*sin(2*PI*t/19)+0.12*sin(2*PI*t/53+1.8)))':eval=frame,haas=left_delay=6.7:right_delay=1.0[air];
        [3:a]bandpass=f=1180:w=310,lowpass=f=2600,volume='if(isnan(t),0,0.006*(0.64+0.21*sin(2*PI*t/23)+0.15*sin(2*PI*t/37+2.6)))':eval=frame,aecho=0.86:0.18:410|970:0.08|0.035,aformat=channel_layouts=stereo[membrane];
        [4:a]volume='if(isnan(t),0,0.052*(0.66+0.34*sin(2*PI*t/61)))':eval=frame,aformat=channel_layouts=stereo[n1];
        [5:a]volume='if(isnan(t),0,0.034*(0.62+0.38*sin(2*PI*t/73+1.1)))':eval=frame,haas=left_delay=1.2:right_delay=9.0[n2];
        [6:a]volume='if(isnan(t),0,0.027*(0.60+0.40*sin(2*PI*t/89+2.2)))':eval=frame,haas=left_delay=9.2:right_delay=1.0[n3];
        [7:a]volume='if(isnan(t),0,0.029*(0.64+0.36*sin(2*PI*t/79+3.4)))':eval=frame,aformat=channel_layouts=stereo[n4];
        [8:a]volume='if(isnan(t),0,0.014*(0.55+0.45*sin(2*PI*t/97+4.3)))':eval=frame,haas=left_delay=1.0:right_delay=8.8[n5];
        [n1][n2][n3][n4][n5]amix=inputs=5:normalize=0,chorus=0.28:0.42:31|43:0.07|0.05:0.08|0.06:0.11|0.08,aecho=0.91:0.18:1360|3210:0.075|0.032,lowpass=f=4200[harmony];
        [ground][windbody][air][membrane][harmony]amix=inputs=5:normalize=0:dropout_transition=0,
          highpass=f=30,lowpass=f=10500,acompressor=threshold=0.30:ratio=1.45:attack=180:release=1800,
          loudnorm=I=-22:TP=-3:LRA=10,afade=t=in:st=0:d=5,afade=t=out:st=$((DURATION - 7)):d=7[out]
      " -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$OUTPUT"
    ;;
  tide)
    # An unresolved, human-voiced low harmonic architecture leads the mix. The
    # shore and vertical water mass remain distant supporting atmosphere.
    ffmpeg -y -nostdin \
      -f lavfi -t "$DURATION" -i "anoisesrc=c=brown:r=48000:a=1:seed=2203" \
      -f lavfi -t "$DURATION" -i "anoisesrc=c=pink:r=48000:a=1:seed=2207" \
      -f lavfi -t "$DURATION" -i "anoisesrc=c=white:r=48000:a=1:seed=2213" \
      -f lavfi -t "$DURATION" -i "anoisesrc=c=pink:r=48000:a=1:seed=2221" \
      -f lavfi -t "$DURATION" -i "sine=frequency=55.00:sample_rate=48000" \
      -f lavfi -t "$DURATION" -i "sine=frequency=82.41:sample_rate=48000" \
      -f lavfi -t "$DURATION" -i "sine=frequency=110.00:sample_rate=48000" \
      -f lavfi -t "$DURATION" -i "sine=frequency=138.59:sample_rate=48000" \
      -f lavfi -t "$DURATION" -i "sine=frequency=164.81:sample_rate=48000" \
      -filter_complex "
        [0:a]lowpass=f=290,volume='if(isnan(t),0,0.032*(0.65+0.22*sin(2*PI*t/19)+0.13*sin(2*PI*t/47+1.0)))':eval=frame,aformat=channel_layouts=stereo[pressure];
        [1:a]highpass=f=75,lowpass=f=1050,volume='if(isnan(t),0,0.029*(0.67+0.21*sin(2*PI*t/14)+0.12*sin(2*PI*t/39+1.5)))':eval=frame,aecho=0.82:0.20:690:0.10,aformat=channel_layouts=stereo[shore];
        [2:a]highpass=f=420,lowpass=f=4700,volume='if(isnan(t),0,0.012*(0.68+0.18*sin(2*PI*t/27)+0.14*sin(2*PI*t/67+2.2)))':eval=frame,haas=left_delay=1.0:right_delay=7.2[vertical];
        [3:a]bandpass=f=760:w=620,volume='if(isnan(t),0,0.014*(0.60+0.25*sin(2*PI*t/31+0.8)+0.15*sin(2*PI*t/83+2.7)))':eval=frame,haas=left_delay=7.0:right_delay=1.1[watermass];
        [4:a]volume='if(isnan(t),0,0.064*(0.70+0.30*sin(2*PI*t/71)))':eval=frame,aformat=channel_layouts=stereo[d1];
        [5:a]volume='if(isnan(t),0,0.048*(0.66+0.34*sin(2*PI*t/89+1.7)))':eval=frame,haas=left_delay=1.2:right_delay=9.8[d2];
        [6:a]volume='if(isnan(t),0,0.032*(0.60+0.40*sin(2*PI*t/103+2.8)))':eval=frame,aformat=channel_layouts=stereo[d3];
        [7:a]volume='if(isnan(t),0,0.025*(0.58+0.42*sin(2*PI*t/97+3.6)))':eval=frame,haas=left_delay=9.9:right_delay=1.0[d4];
        [8:a]volume='if(isnan(t),0,0.018*(0.55+0.45*sin(2*PI*t/109+4.5)))':eval=frame,aformat=channel_layouts=stereo[d5];
        [d1][d2][d3][d4][d5]amix=inputs=5:normalize=0,chorus=0.25:0.38:37|53:0.06|0.045:0.07|0.055:0.10|0.075,aecho=0.92:0.20:1810|4270:0.08|0.033,lowpass=f=2400[dread];
        [pressure][shore][vertical][watermass][dread]amix=inputs=5:normalize=0:dropout_transition=0,
          highpass=f=24,lowpass=f=9800,acompressor=threshold=0.28:ratio=1.7:attack=220:release=2100,
          loudnorm=I=-20:TP=-2.5:LRA=11,afade=t=in:st=0:d=6,afade=t=out:st=$((DURATION - 8)):d=8[out]
      " -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$OUTPUT"
    ;;
  ceramics)
    # A warm, deliberately voiced ambient ensemble is the primary experience.
    # Kiln convection, ventilation, and hull transfer sit behind it as room tone.
    ffmpeg -y -nostdin \
      -f lavfi -t "$DURATION" -i "anoisesrc=c=brown:r=48000:a=1:seed=3301" \
      -f lavfi -t "$DURATION" -i "anoisesrc=c=pink:r=48000:a=1:seed=3307" \
      -f lavfi -t "$DURATION" -i "anoisesrc=c=white:r=48000:a=1:seed=3313" \
      -f lavfi -t "$DURATION" -i "anoisesrc=c=pink:r=48000:a=1:seed=3319" \
      -f lavfi -t "$DURATION" -i "sine=frequency=65.41:sample_rate=48000" \
      -f lavfi -t "$DURATION" -i "sine=frequency=130.81:sample_rate=48000" \
      -f lavfi -t "$DURATION" -i "sine=frequency=196.00:sample_rate=48000" \
      -f lavfi -t "$DURATION" -i "sine=frequency=246.94:sample_rate=48000" \
      -f lavfi -t "$DURATION" -i "sine=frequency=293.66:sample_rate=48000" \
      -f lavfi -t "$DURATION" -i "sine=frequency=392.00:sample_rate=48000" \
      -filter_complex "
        [0:a]lowpass=f=190,volume='if(isnan(t),0,0.019*(0.78+0.14*sin(2*PI*t/41)+0.08*sin(2*PI*t/91+1.1)))':eval=frame,aformat=channel_layouts=stereo[hull];
        [1:a]highpass=f=105,lowpass=f=980,volume='if(isnan(t),0,0.017*(0.72+0.17*sin(2*PI*t/31)+0.11*sin(2*PI*t/73+1.4)))':eval=frame,haas=left_delay=1.0:right_delay=5.5[vent];
        [2:a]highpass=f=750,lowpass=f=4800,volume='if(isnan(t),0,0.006*(0.70+0.18*sin(2*PI*t/21)+0.12*sin(2*PI*t/47+1.6)))':eval=frame,haas=left_delay=5.7:right_delay=1.0[convection];
        [3:a]bandpass=f=430:w=240,volume='if(isnan(t),0,0.011*(0.68+0.19*sin(2*PI*t/29)+0.13*sin(2*PI*t/59+2.4)))':eval=frame,aecho=0.88:0.12:520|1380:0.06|0.025,aformat=channel_layouts=stereo[kiln];
        [4:a]volume='if(isnan(t),0,0.041*(0.74+0.26*sin(2*PI*t/83)))':eval=frame,aformat=channel_layouts=stereo[c1];
        [5:a]volume='if(isnan(t),0,0.052*(0.70+0.30*sin(2*PI*t/67+0.9)))':eval=frame,aformat=channel_layouts=stereo[c2];
        [6:a]volume='if(isnan(t),0,0.034*(0.66+0.34*sin(2*PI*t/79+1.8)))':eval=frame,haas=left_delay=1.1:right_delay=9.9[c3];
        [7:a]volume='if(isnan(t),0,0.025*(0.62+0.38*sin(2*PI*t/97+2.7)))':eval=frame,haas=left_delay=10.0:right_delay=1.0[c4];
        [8:a]volume='if(isnan(t),0,0.023*(0.64+0.36*sin(2*PI*t/89+3.5)))':eval=frame,aformat=channel_layouts=stereo[c5];
        [9:a]volume='if(isnan(t),0,0.014*(0.58+0.42*sin(2*PI*t/107+4.4)))':eval=frame,haas=left_delay=1.0:right_delay=9.6[c6];
        [c1][c2][c3][c4][c5][c6]amix=inputs=6:normalize=0,chorus=0.38:0.48:32|47:0.09|0.065:0.11|0.08:0.14|0.10,aecho=0.90:0.18:990|2380:0.07|0.03,lowpass=f=4600[warmth];
        [hull][vent][convection][kiln][warmth]amix=inputs=5:normalize=0:dropout_transition=0,
          highpass=f=28,lowpass=f=10000,acompressor=threshold=0.31:ratio=1.5:attack=170:release=1700,
          loudnorm=I=-21:TP=-3:LRA=9,afade=t=in:st=0:d=5,afade=t=out:st=$((DURATION - 7)):d=7[out]
      " -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$OUTPUT"
    ;;
  *)
    echo "ERROR: unsupported mode: $MODE" >&2
    exit 2
    ;;
esac

echo "Done -> $OUTPUT"
