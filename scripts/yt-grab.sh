#!/bin/bash
# Download YouTube audio as mp3 directly into audio/queue/.
# Single video: ./yt-grab.sh <url> [name]
# Channel/playlist: ./yt-grab.sh <channel_or_playlist_url>   (auto-uses video titles)

set -e
URL="$1"
NAME="$2"

if [ -z "$URL" ]; then
  echo "Usage: $0 <youtube_url> [name]"
  echo "  Single video with name: $0 https://youtu.be/X erebus"
  echo "  Channel bulk:           $0 https://youtube.com/@channelname"
  exit 1
fi

DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$DIR/audio/queue"

mkdir -p "$DEST"

if [ -n "$NAME" ]; then
  yt-dlp -x --audio-format mp3 -o "$DEST/${NAME}.mp3" "$URL"
  echo "Saved -> $DEST/${NAME}.mp3"
else
  yt-dlp -x --audio-format mp3 -o "$DEST/%(title)s.%(ext)s" "$URL"
  echo "Saved channel/playlist to $DEST/"
fi
