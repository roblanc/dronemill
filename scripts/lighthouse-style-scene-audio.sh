#!/bin/bash
# Mix a LatentScore musical bed in the music-forward style used by Lighthouse.
# Usage: ./scripts/lighthouse-style-scene-audio.sh <mode> <music> <output> [duration=120]

set -euo pipefail

MODE="${1:-}"
MUSIC="${2:-}"
OUTPUT="${3:-}"
DURATION="${4:-120}"

if [ ! -f "$MUSIC" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: $0 <noonbloom|tide|ceramics|ferry|video-store|gypsum|tree-ring|protoceratops|atrium|blue-pressure|baggage-claim|salt-archive|cloud-roots|asteroid-kitchen|rewind-season|indoor-stars|mangrove-waterlines|oldest-thunder> <music> <output> [duration=120]" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

case "$MODE" in
  noonbloom)
    MUSIC_FILTER="highpass=f=42,lowpass=f=12500,chorus=0.18:0.28:31|47:0.035|0.025:0.04|0.03:0.08|0.10"
    BED1_FILTER="highpass=f=100,lowpass=f=1250"
    BED2_FILTER="highpass=f=750,lowpass=f=4300"
    BED1_VOLUME="0.018*(0.72+0.18*sin(2*PI*t/31)+0.10*sin(2*PI*t/73+1.2))"
    BED2_VOLUME="0.006*(0.70+0.18*sin(2*PI*t/23)+0.12*sin(2*PI*t/59+2.1))"
    SEED1=4101
    SEED2=4109
    ;;
  tide)
    MUSIC_FILTER="highpass=f=25,lowpass=f=8500,aecho=0.88:0.12:1700|3900:0.045|0.018"
    BED1_FILTER="lowpass=f=390"
    BED2_FILTER="highpass=f=320,lowpass=f=2400"
    BED1_VOLUME="0.030*(0.66+0.22*sin(2*PI*t/19)+0.12*sin(2*PI*t/53+1.0))"
    BED2_VOLUME="0.011*(0.68+0.19*sin(2*PI*t/29)+0.13*sin(2*PI*t/71+2.2))"
    SEED1=4201
    SEED2=4211
    ;;
  ceramics)
    MUSIC_FILTER="highpass=f=32,lowpass=f=11000,chorus=0.20:0.30:34|51:0.04|0.028:0.05|0.035:0.09|0.11"
    BED1_FILTER="lowpass=f=260"
    BED2_FILTER="highpass=f=180,lowpass=f=1450"
    BED1_VOLUME="0.017*(0.78+0.14*sin(2*PI*t/43)+0.08*sin(2*PI*t/89+1.1))"
    BED2_VOLUME="0.009*(0.72+0.17*sin(2*PI*t/37)+0.11*sin(2*PI*t/79+1.8))"
    SEED1=4301
    SEED2=4307
    ;;
  ferry)
    MUSIC_FILTER="highpass=f=40,lowpass=f=12000,chorus=0.16:0.26:38|53:0.035|0.025:0.04|0.03:0.08|0.10"
    BED1_FILTER="lowpass=f=320"
    BED2_FILTER="highpass=f=600,lowpass=f=3200"
    BED1_VOLUME="0.024*(0.70+0.20*sin(2*PI*t/41)+0.10*sin(2*PI*t/97+1.3))"
    BED2_VOLUME="0.007*(0.72+0.16*sin(2*PI*t/29)+0.12*sin(2*PI*t/67+2.0))"
    SEED1=4401
    SEED2=4407
    ;;
  video-store)
    MUSIC_FILTER="highpass=f=50,lowpass=f=9500,chorus=0.14:0.24:45|61:0.03|0.022:0.04|0.03:0.08|0.10"
    BED1_FILTER="lowpass=f=240"
    BED2_FILTER="bandpass=f=1200:w=1400"
    BED1_VOLUME="0.018*(0.76+0.15*sin(2*PI*t/53)+0.09*sin(2*PI*t/113+1.1))"
    BED2_VOLUME="0.005*(0.70+0.20*sin(2*PI*t/31)+0.10*sin(2*PI*t/83+1.7))"
    SEED1=4501
    SEED2=4509
    ;;
  gypsum)
    MUSIC_FILTER="highpass=f=30,lowpass=f=13000,aecho=0.86:0.12:2300|4800:0.04|0.015"
    BED1_FILTER="bandpass=f=500:w=1000"
    BED2_FILTER="highpass=f=3600,lowpass=f=8500"
    BED1_VOLUME="0.020*(0.66+0.22*sin(2*PI*t/37)+0.12*sin(2*PI*t/89+0.9))"
    BED2_VOLUME="0.006*(0.70+0.17*sin(2*PI*t/47)+0.13*sin(2*PI*t/101+2.3))"
    SEED1=4601
    SEED2=4611
    ;;
  tree-ring)
    MUSIC_FILTER="highpass=f=35,lowpass=f=11000,chorus=0.17:0.27:34|49:0.035|0.025:0.045|0.03:0.08|0.10"
    BED1_FILTER="lowpass=f=420"
    BED2_FILTER="highpass=f=500,lowpass=f=2600"
    BED1_VOLUME="0.022*(0.70+0.18*sin(2*PI*t/43)+0.12*sin(2*PI*t/103+1.2))"
    BED2_VOLUME="0.008*(0.74+0.15*sin(2*PI*t/27)+0.11*sin(2*PI*t/71+1.9))"
    SEED1=4701
    SEED2=4709
    ;;
  protoceratops)
    MUSIC_FILTER="highpass=f=35,lowpass=f=11500,chorus=0.19:0.29:36|52:0.04|0.028:0.05|0.035:0.09|0.11"
    BED1_FILTER="bandpass=f=600:w=1900"
    BED2_FILTER="highpass=f=500,lowpass=f=3400"
    BED1_VOLUME="0.021*(0.78+0.13*sin(2*PI*t/33)+0.09*sin(2*PI*t/79+1.0))"
    BED2_VOLUME="0.007*(0.72+0.17*sin(2*PI*t/41)+0.11*sin(2*PI*t/97+2.1))"
    SEED1=4801
    SEED2=4811
    ;;
  atrium)
    MUSIC_FILTER="highpass=f=32,lowpass=f=11500,aecho=0.9:0.14:2800|5200:0.05|0.02"
    BED1_FILTER="lowpass=f=280"
    BED2_FILTER="highpass=f=900,lowpass=f=3600"
    BED1_VOLUME="0.022*(0.64+0.20*sin(2*PI*t/41)+0.12*sin(2*PI*t/97+0.9))"
    BED2_VOLUME="0.006*(0.66+0.17*sin(2*PI*t/31)+0.12*sin(2*PI*t/83+2.2))"
    SEED1=4901
    SEED2=4913
    ;;
  blue-pressure)
    MUSIC_FILTER="highpass=f=22,lowpass=f=7200,aecho=0.9:0.10:3100|5800:0.04|0.016"
    BED1_FILTER="bandpass=f=180:w=240"
    BED2_FILTER="highpass=f=2600,lowpass=f=6800"
    BED1_VOLUME="0.026*(0.66+0.20*sin(2*PI*t/47)+0.12*sin(2*PI*t/109+1.1))"
    BED2_VOLUME="0.005*(0.70+0.16*sin(2*PI*t/37)+0.12*sin(2*PI*t/101+1.9))"
    SEED1=5001
    SEED2=5011
    ;;
  baggage-claim)
    MUSIC_FILTER="highpass=f=45,lowpass=f=12500,chorus=0.16:0.26:41|57:0.035|0.024:0.042|0.03:0.08|0.10"
    BED1_FILTER="lowpass=f=340"
    BED2_FILTER="bandpass=f=1600:w=1500"
    BED1_VOLUME="0.017*(0.80+0.13*sin(2*PI*t/37)+0.07*sin(2*PI*t/83+1.2))"
    BED2_VOLUME="0.005*(0.74+0.16*sin(2*PI*t/43)+0.10*sin(2*PI*t/97+2.0))"
    SEED1=5101
    SEED2=5107
    ;;
  salt-archive)
    MUSIC_FILTER="highpass=f=24,lowpass=f=8200,aecho=0.92:0.16:3600|6200:0.045|0.018"
    BED1_FILTER="lowpass=f=220"
    BED2_FILTER="highpass=f=1400,lowpass=f=4200"
    BED1_VOLUME="0.026*(0.62+0.22*sin(2*PI*t/53)+0.12*sin(2*PI*t/113+1.0))"
    BED2_VOLUME="0.005*(0.66+0.18*sin(2*PI*t/29)+0.12*sin(2*PI*t/79+2.3))"
    SEED1=5201
    SEED2=5209
    ;;
  cloud-roots)
    MUSIC_FILTER="highpass=f=48,lowpass=f=13500,chorus=0.15:0.25:39|55:0.035|0.026:0.043|0.03:0.08|0.10"
    BED1_FILTER="bandpass=f=420:w=900"
    BED2_FILTER="highpass=f=2100,lowpass=f=7500"
    BED1_VOLUME="0.016*(0.82+0.12*sin(2*PI*t/31)+0.06*sin(2*PI*t/71+1.1))"
    BED2_VOLUME="0.006*(0.76+0.15*sin(2*PI*t/41)+0.10*sin(2*PI*t/89+2.1))"
    SEED1=5301
    SEED2=5311
    ;;
  asteroid-kitchen)
    MUSIC_FILTER="highpass=f=40,lowpass=f=9500,chorus=0.18:0.28:33|49:0.035|0.025:0.04|0.03:0.08|0.10"
    BED1_FILTER="lowpass=f=320"
    BED2_FILTER="bandpass=f=800:w=1600"
    BED1_VOLUME="0.022*(0.78+0.14*sin(2*PI*t/39)+0.08*sin(2*PI*t/97+1.1))"
    BED2_VOLUME="0.008*(0.74+0.16*sin(2*PI*t/31)+0.10*sin(2*PI*t/83+1.9))"
    SEED1=5401
    SEED2=5407
    ;;
  rewind-season)
    MUSIC_FILTER="highpass=f=55,lowpass=f=10500,chorus=0.15:0.25:44|59:0.03|0.022:0.04|0.03:0.08|0.10"
    BED1_FILTER="bandpass=f=120:w=120"
    BED2_FILTER="highpass=f=1800,lowpass=f=6200"
    BED1_VOLUME="0.020*(0.72+0.17*sin(2*PI*t/47)+0.11*sin(2*PI*t/109+1.2))"
    BED2_VOLUME="0.006*(0.70+0.16*sin(2*PI*t/37)+0.12*sin(2*PI*t/97+2.0))"
    SEED1=5501
    SEED2=5509
    ;;
  indoor-stars)
    MUSIC_FILTER="highpass=f=28,lowpass=f=11500,aecho=0.9:0.14:2900|5100:0.05|0.02"
    BED1_FILTER="lowpass=f=260"
    BED2_FILTER="highpass=f=2400,lowpass=f=7000"
    BED1_VOLUME="0.022*(0.66+0.20*sin(2*PI*t/43)+0.12*sin(2*PI*t/103+0.9))"
    BED2_VOLUME="0.006*(0.68+0.17*sin(2*PI*t/29)+0.12*sin(2*PI*t/79+2.2))"
    SEED1=5601
    SEED2=5607
    ;;
  mangrove-waterlines)
    MUSIC_FILTER="highpass=f=24,lowpass=f=7200,aecho=0.92:0.16:3400|5900:0.05|0.018"
    BED1_FILTER="lowpass=f=200"
    BED2_FILTER="bandpass=f=1000:w=900"
    BED1_VOLUME="0.024*(0.64+0.21*sin(2*PI*t/51)+0.12*sin(2*PI*t/113+1.0))"
    BED2_VOLUME="0.005*(0.66+0.18*sin(2*PI*t/41)+0.12*sin(2*PI*t/89+2.1))"
    SEED1=5701
    SEED2=5709
    ;;
  oldest-thunder)
    MUSIC_FILTER="highpass=f=30,lowpass=f=10000,aecho=0.88:0.12:2200|4400:0.04|0.016"
    BED1_FILTER="lowpass=f=300"
    BED2_FILTER="highpass=f=2500,lowpass=f=8000"
    BED1_VOLUME="0.026*(0.66+0.20*sin(2*PI*t/49)+0.12*sin(2*PI*t/107+1.1))"
    BED2_VOLUME="0.007*(0.70+0.17*sin(2*PI*t/33)+0.12*sin(2*PI*t/83+1.8))"
    SEED1=5801
    SEED2=5807
    ;;
  *)
    echo "ERROR: unsupported mode: $MODE" >&2
    exit 2
    ;;
esac

ffmpeg -y -nostdin \
  -stream_loop -1 -i "$MUSIC" \
  -f lavfi -t "$DURATION" -i "anoisesrc=c=brown:r=48000:a=1:seed=${SEED1}" \
  -f lavfi -t "$DURATION" -i "anoisesrc=c=pink:r=48000:a=1:seed=${SEED2}" \
  -filter_complex "
    [0:a]atrim=duration=${DURATION},asetpts=N/SR/TB,${MUSIC_FILTER},volume=0.82,aformat=channel_layouts=stereo[music];
    [1:a]${BED1_FILTER},volume='if(isnan(t),0,${BED1_VOLUME})':eval=frame,aformat=channel_layouts=stereo[bed1];
    [2:a]${BED2_FILTER},volume='if(isnan(t),0,${BED2_VOLUME})':eval=frame,haas=left_delay=2.0:right_delay=12.0[bed2];
    [music][bed1][bed2]amix=inputs=3:normalize=0:dropout_transition=0,
      highpass=f=24,lowpass=f=14000,acompressor=threshold=0.34:ratio=1.6:attack=160:release=1200,
      loudnorm=I=-18:TP=-1.5:LRA=9,afade=t=in:st=0:d=4,afade=t=out:st=$((DURATION - 6)):d=6,
      asetpts=N/SR/TB,apad=pad_dur=1,atrim=duration=${DURATION}[out]
  " -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$OUTPUT"

echo "Done -> $OUTPUT"
