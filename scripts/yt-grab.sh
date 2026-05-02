#!/bin/bash
# Usage: ./yt-grab.sh <youtube_url> <name>
# Downloads audio as mp3 to ../audio/<name>.mp3

set -e
URL="$1"
NAME="$2"

if [ -z "$URL" ] || [ -z "$NAME" ]; then
  echo "Usage: $0 <youtube_url> <name>"
  exit 1
fi

DIR="$(cd "$(dirname "$0")/.." && pwd)"
yt-dlp -x --audio-format mp3 -o "$DIR/audio/${NAME}.mp3" "$URL"
echo "Saved -> $DIR/audio/${NAME}.mp3"
