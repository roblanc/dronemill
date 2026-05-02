#!/bin/bash
# Watches audio/ root for new .mp3 files and moves them to audio/queue/.
# Run in background tab while yt-dlp downloads to audio/ root.
#
# Usage: ./audio-watcher.sh [poll_interval_seconds=15]
# Stop: Ctrl+C

set -e

DIR="$(cd "$(dirname "$0")/.." && pwd)"
INTERVAL="${1:-15}"

echo ">> Watching $DIR/audio/ for new .mp3 files"
echo ">> Moving any to $DIR/audio/queue/ every ${INTERVAL}s"
echo ">> Ctrl+C to stop"
echo ""

while true; do
  # Find files in audio/ root (not subdirs), modified >5s ago (avoid in-progress)
  COUNT=0
  for f in "$DIR"/audio/*.mp3; do
    [ -f "$f" ] || continue
    AGE=$(($(date +%s) - $(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f")))
    if [ "$AGE" -gt 5 ]; then
      mv "$f" "$DIR/audio/queue/"
      COUNT=$((COUNT + 1))
    fi
  done

  if [ "$COUNT" -gt 0 ]; then
    TOTAL=$(ls "$DIR/audio/queue/"*.mp3 2>/dev/null | wc -l | xargs)
    echo "$(date +%H:%M:%S) — moved $COUNT, queue total: $TOTAL"
  fi

  sleep "$INTERVAL"
done
