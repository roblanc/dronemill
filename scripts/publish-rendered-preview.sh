#!/bin/bash
# Publish an already-rendered review video into Jellyfin's Videos library.
# Usage: ./scripts/publish-rendered-preview.sh <video> <title> [slug]

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/_lib.sh"
SOURCE="${1:-}"
TITLE="${2:-}"
SLUG="${3:-}"
JELLYFIN_ROOT="${JELLYFIN_PREVIEW_DIR:-/srv/media/videos/DroneMill Previews}"

if [ ! -f "$SOURCE" ] || [ -z "$TITLE" ]; then
  echo "Usage: $0 <video> <title> [slug]" >&2
  exit 1
fi

if [ -z "$SLUG" ]; then
  SLUG=$(slugify "$TITLE")
fi

DEST="$JELLYFIN_ROOT/$SLUG"
VIDEO="$DEST/$SLUG.mp4"
mkdir -p "$DEST"

ffmpeg -y -nostdin -i "$SOURCE" -map 0 -c copy -movflags +faststart "$VIDEO"
ffmpeg -y -nostdin -ss 3 -i "$SOURCE" -frames:v 1 -update 1 "$DEST/poster.jpg"

XML_TITLE=${TITLE//&/&amp;}
XML_TITLE=${XML_TITLE//</&lt;}
XML_TITLE=${XML_TITLE//>/&gt;}
cat > "$DEST/$SLUG.nfo" <<EOF
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<movie>
  <title>$XML_TITLE</title>
  <sorttitle>$XML_TITLE</sorttitle>
  <plot>DroneMill scene-aware animated comparison preview.</plot>
  <studio>DroneMill</studio>
  <tag>DroneMill Preview</tag>
</movie>
EOF

echo "Published -> $VIDEO"
