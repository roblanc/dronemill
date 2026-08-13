#!/bin/bash
# Publish an image + audio review copy into Jellyfin's Videos library.
# Usage: ./scripts/publish-jellyfin-preview.sh <image> <audio> <title> [slug]

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"
IMAGE="${1:-}"
AUDIO="${2:-}"
TITLE="${3:-}"
SLUG="${4:-}"
JELLYFIN_ROOT="${JELLYFIN_PREVIEW_DIR:-/srv/media/videos/DroneMill Previews}"

if [ -z "$IMAGE" ] || [ -z "$AUDIO" ] || [ -z "$TITLE" ]; then
  echo "Usage: $0 <image> <audio> <title> [slug]" >&2
  exit 1
fi

if [ ! -f "$IMAGE" ] || [ ! -f "$AUDIO" ]; then
  echo "ERROR: image or audio input does not exist" >&2
  exit 1
fi

if [ -z "$SLUG" ]; then
  SLUG=$(slugify "$TITLE")
fi

DEST="$JELLYFIN_ROOT/$SLUG"
VIDEO="$DEST/$SLUG.mp4"
DURATION=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$AUDIO")
mkdir -p "$DEST"

# Low frame rate keeps review copies small while remaining widely playable.
ffmpeg -y -loop 1 -framerate 1 -i "$IMAGE" -i "$AUDIO" \
  -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,format=yuv420p" \
  -c:v libx264 -preset veryfast -tune stillimage -crf 24 -r 1 \
  -c:a aac -b:a 192k -ar 48000 -ac 2 -t "$DURATION" -movflags +faststart \
  "$VIDEO"

ffmpeg -y -i "$IMAGE" \
  -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black" \
  -frames:v 1 -update 1 "$DEST/poster.jpg"

XML_TITLE=${TITLE//&/&amp;}
XML_TITLE=${XML_TITLE//</&lt;}
XML_TITLE=${XML_TITLE//>/&gt;}
cat > "$DEST/$SLUG.nfo" <<EOF
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<movie>
  <title>$XML_TITLE</title>
  <sorttitle>$XML_TITLE</sorttitle>
  <plot>DroneMill image and ambient audio review preview.</plot>
  <studio>DroneMill</studio>
  <tag>DroneMill Preview</tag>
</movie>
EOF

echo "Published -> $VIDEO"
