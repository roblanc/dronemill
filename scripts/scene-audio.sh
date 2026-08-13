#!/bin/bash
# Mix a musical bed with profile-specific procedural environmental audio.
# Usage: ./scripts/scene-audio.sh <profile.json> <music> <output> [duration=180]

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILE="${1:-}"
MUSIC="${2:-}"
OUTPUT="${3:-}"
DURATION="${4:-180}"

if [ ! -f "$PROFILE" ] || [ ! -f "$MUSIC" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: $0 <profile.json> <music> <output> [duration=180]" >&2
  exit 1
fi

eval "$(python3 "$DIR/scene-profile.py" "$PROFILE")"
if [ "$ID" != "lighthouse" ]; then
  echo "ERROR: unsupported audio profile: $ID" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
HORN_2=$(awk "BEGIN {print $AUDIO_FOGHORN_FREQUENCY * 1.5}")

ffmpeg -y -nostdin \
  -stream_loop -1 -i "$MUSIC" \
  -f lavfi -t "$DURATION" -i "anoisesrc=c=brown:r=48000:a=1" \
  -f lavfi -t "$DURATION" -i "anoisesrc=c=white:r=48000:a=1" \
  -f lavfi -t "$DURATION" -i "anoisesrc=c=pink:r=48000:a=1" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${AUDIO_FOGHORN_FREQUENCY}:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${HORN_2}:sample_rate=48000" \
  -filter_complex "
    [0:a]atrim=duration=${DURATION},asetpts=N/SR/TB,volume=${AUDIO_MUSIC_VOLUME},aformat=channel_layouts=stereo[music];
    [1:a]lowpass=f=430,volume='if(isnan(t),${AUDIO_OCEAN_VOLUME},${AUDIO_OCEAN_VOLUME}*(0.64+0.36*sin(2*PI*t/13)))':eval=frame,aformat=channel_layouts=stereo[ocean];
    [2:a]highpass=f=380,lowpass=f=3600,tremolo=f=0.105:d=0.88,volume=${AUDIO_SURF_VOLUME},aecho=0.8:0.35:730:0.18,aformat=channel_layouts=stereo[surf];
    [3:a]highpass=f=120,lowpass=f=1800,volume='if(isnan(t),${AUDIO_WIND_VOLUME},${AUDIO_WIND_VOLUME}*(0.7+0.3*sin(2*PI*t/24)))':eval=frame,haas=left_delay=2.1:right_delay=14.7,lowpass=f=2400[wind];
    [4:a]volume=${AUDIO_FOGHORN_VOLUME}:enable='between(t,22,30)+between(t,78,87)+between(t,142,152)'[h1];
    [5:a]volume=0.022:enable='between(t,22,30)+between(t,78,87)+between(t,142,152)'[h2];
    [h1][h2]amix=inputs=2:normalize=0,aecho=0.85:0.45:1100|2600:0.25|0.12,lowpass=f=900,aformat=channel_layouts=stereo[horn];
    [music][ocean][surf][wind][horn]amix=inputs=5:normalize=0:dropout_transition=3,
    highpass=f=25,lowpass=f=14000,acompressor=threshold=0.32:ratio=2.5:attack=120:release=900,
    loudnorm=I=-18:TP=-1.5:LRA=9,afade=t=in:st=0:d=4,afade=t=out:st=$((DURATION - 6)):d=6[out]
  " \
  -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$OUTPUT"

echo "Done -> $OUTPUT"
