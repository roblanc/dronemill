#!/bin/bash
# Publish an already-rendered review video into Jellyfin's Videos library.
# Usage: ./scripts/publish-rendered-preview.sh <video> <title> [slug]

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/_lib.sh"
SOURCE="${1:-}"
TITLE="${2:-}"
SLUG="${3:-}"
MEDIA_ROOT="${DRONEMILL_MEDIA_DIR:-/DATA/Media}"

if [ ! -f "$SOURCE" ] || [ -z "$TITLE" ]; then
  echo "Usage: $0 <video> <title> [slug]" >&2
  exit 1
fi

if [ -z "$SLUG" ]; then
  SLUG=$(slugify "$TITLE")
fi

VIDEO="$MEDIA_ROOT/$SLUG.mp4"
mkdir -p "$MEDIA_ROOT"

ffmpeg -y -nostdin -i "$SOURCE" -map 0 -c copy -movflags +faststart "$VIDEO"

echo "Published -> $VIDEO"
