#!/bin/bash
# Usage: ./upload-yt.sh <video> <title> <desc_file> <thumbnail> [privacy=unlisted] [tags_csv] [publishAt]
# publishAt: ISO 8601 UTC, e.g. 2026-05-04T18:00:00Z (must be future, forces privacy=private)
# tags_csv:  comma-separated, e.g. "ambient,cosmic horror,sleep music"

set -e

VIDEO="$1"
TITLE="$2"
DESC="$3"
THUMB="$4"
PRIVACY="${5:-unlisted}"
TAGS_CSV="${6:-ambient,cosmic horror,dark ambient,sleep ambient,study music,1 hour ambient,sci-fi ambient,deep space,timeless ambience}"
PUBLISH_AT="$7"

if [ -z "$VIDEO" ] || [ -z "$TITLE" ] || [ -z "$DESC" ] || [ -z "$THUMB" ]; then
  echo "Usage: $0 <video> <title> <desc_file> <thumbnail> [privacy=unlisted] [tags_csv] [publishAt]"
  exit 1
fi

# If publishAt is set, force privacy=private (YT requirement for scheduled videos)
if [ -n "$PUBLISH_AT" ]; then
  if [ "$PRIVACY" != "private" ]; then
    echo "INFO: publishAt set, forcing privacy=private (required for scheduling)"
    PRIVACY="private"
  fi
fi

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
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

# Build metaJSON dynamically — handles multi-line descriptions + scheduling cleanly
# Cross-platform mktemp: macOS needs no XXXXXX; Linux requires it.
META="/tmp/dronemill_meta_$$_$(date +%s).json"
DESCRIPTION=$(cat "$DESC")

# Porjo's youtubeuploader uses a flat JSON structure or specific snippet/status.
# We'll provide both or a flat one that works with most versions.
python3 -c "
import json, sys
title, description, privacy, tags_csv, publish_at = sys.argv[1:6]
meta = {
    'title': title,
    'description': description,
    'tags': [t.strip() for t in tags_csv.split(',') if t.strip()],
    'privacyStatus': privacy,
    'categoryId': '10',
    'selfDeclaredMadeForKids': False
}
if publish_at:
    if publish_at.endswith('Z'):
        publish_at = publish_at[:-1] + '-00:00'
    meta['publishAt'] = publish_at

# For newer versions that expect snippet/status:
meta_full = {
    'snippet': {
        'title': title,
        'description': description,
        'tags': meta['tags'],
        'categoryId': '10'
    },
    'status': {
        'privacyStatus': privacy,
        'publishAt': publish_at if publish_at else None,
        'selfDeclaredMadeForKids': False
    }
}
# We'll use the flat one as it's more common for this CLI
print(json.dumps(meta, indent=2))
" "$TITLE" "$DESCRIPTION" "$PRIVACY" "$TAGS_CSV" "$PUBLISH_AT" > "$META"

echo ">> Uploading: $TITLE"
echo ">> Tags: $TAGS_CSV"

UPLOAD_LOG=$(mktemp)
youtubeuploader \
  -filename "$VIDEO" \
  -title "$TITLE" \
  -description "$DESCRIPTION" \
  -metaJSON "$META" \
  -thumbnail "$THUMB" \
  -secrets "$CREDS" \
  -cache "$TOKEN" 2>&1 | tee "$UPLOAD_LOG"

VIDEO_ID=$(grep -o 'Video ID: [a-zA-Z0-9_-]\+' "$UPLOAD_LOG" | awk '{print $3}' | tail -n 1 || true)
rm -f "$UPLOAD_LOG"

# Write to upload history log
HISTORY_FILE="$ROOT/output/upload_history.json"
python3 -c "
import os, json, datetime, sys
history_file, title, description, tags, privacy, publish_at, thumbnail, local_path, video_id = sys.argv[1:10]
entry = {
    'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
    'title': title,
    'description': description,
    'tags': [t.strip() for t in tags.split(',') if t.strip()],
    'privacy': privacy,
    'publish_at': publish_at if publish_at else None,
    'thumbnail': os.path.basename(thumbnail),
    'local_path': os.path.basename(local_path),
    'video_id': video_id if video_id else None,
    'youtube_url': f'https://www.youtube.com/watch?v={video_id}' if video_id else None,
    'short_url': f'https://youtu.be/{video_id}' if video_id else None
}
history = []
if os.path.exists(history_file):
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
            if not isinstance(history, list):
                history = []
    except Exception as e:
        sys.stderr.write(f'Warn: Could not parse history file: {e}\n')
history.append(entry)
with open(history_file, 'w', encoding='utf-8') as f:
    json.dump(history, f, indent=2)
" "$HISTORY_FILE" "$TITLE" "$DESCRIPTION" "$TAGS_CSV" "$PRIVACY" "$PUBLISH_AT" "$THUMB" "$VIDEO" "$VIDEO_ID"

# Clean up local video file to save space
if [ -f "$VIDEO" ]; then
  rm -f "$VIDEO"
  echo "INFO: Deleted local video file: $VIDEO to save space."
fi

# Clean up compressed thumbnail if created
if [ -n "$COMPRESSED" ] && [ -f "$COMPRESSED" ]; then
  rm -f "$COMPRESSED"
  echo "INFO: Deleted temporary compressed thumbnail: $COMPRESSED"
fi

rm "$META"
if [ -n "$PUBLISH_AT" ]; then
  echo "Scheduled: $TITLE → publishes at $PUBLISH_AT UTC"
else
  echo "Uploaded: $TITLE (privacy=$PRIVACY)"
fi
