#!/bin/bash
# Usage: ./upload-yt.sh <video_path> <title> <desc_file> <thumbnail> [privacy=unlisted]
# Example: ./upload-yt.sh ../output/erebus_v1.mp4 "frozen 169 years..." ../descriptions/erebus_v1.txt ../images/erebus_cover.png

set -e

VIDEO="$1"
TITLE="$2"
DESC="$3"
THUMB="$4"
PRIVACY="${5:-unlisted}"

if [ -z "$VIDEO" ] || [ -z "$TITLE" ] || [ -z "$DESC" ] || [ -z "$THUMB" ]; then
  echo "Usage: $0 <video> <title> <desc_file> <thumbnail> [privacy=unlisted]"
  exit 1
fi

CREDS="$HOME/.youtubeuploader/client_secrets.json"
TOKEN="$HOME/.youtubeuploader/request.token"

# Single-instance guard — prevent duplicate uploads
LOCKFILE="$HOME/.youtubeuploader/upload.lock"
if [ -f "$LOCKFILE" ]; then
  PID=$(cat "$LOCKFILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "ERROR: another upload running (PID $PID). Wait for it or kill: kill $PID"
    exit 1
  fi
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT

if [ ! -f "$CREDS" ]; then
  echo "ERROR: client_secrets.json missing. See SETUP-YOUTUBE.md"
  exit 1
fi

if [ ! -f "$DESC" ]; then
  echo "ERROR: description file not found: $DESC"
  exit 1
fi

# YT thumbnail limit = 2MB. Auto-compress if oversized.
THUMB_SIZE=$(stat -f%z "$THUMB" 2>/dev/null || stat -c%s "$THUMB")
if [ "$THUMB_SIZE" -gt 2000000 ]; then
  echo "Thumbnail $THUMB is ${THUMB_SIZE} bytes (>2MB). Compressing..."
  COMPRESSED="${THUMB%.*}_compressed.jpg"
  ffmpeg -y -i "$THUMB" -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black" -q:v 4 "$COMPRESSED" 2>/dev/null
  THUMB="$COMPRESSED"
  echo "Using compressed thumbnail: $THUMB ($(stat -f%z "$THUMB" 2>/dev/null || stat -c%s "$THUMB") bytes)"
fi

# Build metaJSON dynamically — handles multi-line descriptions cleanly
META=$(mktemp -t dronemill_meta).json
DESCRIPTION=$(cat "$DESC")

# Use python for safe JSON encoding (handles quotes, newlines, unicode)
python3 -c "
import json, sys
meta = {
    'snippet': {
        'title': sys.argv[1],
        'description': sys.argv[2],
        'tags': ['ambient','cosmic horror','dark ambient','sleep ambient','study music','1 hour ambient','sci-fi ambient','deep space','timeless ambience'],
        'categoryId': '10',
    },
    'status': {
        'privacyStatus': sys.argv[3],
    }
}
print(json.dumps(meta, indent=2))
" "$TITLE" "$DESCRIPTION" "$PRIVACY" > "$META"

youtubeuploader \
  -filename "$VIDEO" \
  -metaJSON "$META" \
  -thumbnail "$THUMB" \
  -secrets "$CREDS" \
  -cache "$TOKEN"

rm "$META"
echo "Uploaded: $TITLE"
