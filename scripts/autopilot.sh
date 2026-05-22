#!/bin/bash
# Autopilot wrapper for cron / launchd.
# Ensures the correct PATH environment is set so that homebrew-installed utilities (ffmpeg, yt-dlp, youtubeuploader) are accessible.

set -e

# Load macOS homebrew path if it exists
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

# If you have an .env file in the root, source it (optional, to load API keys)
if [ -f "$ROOT/.env" ]; then
  export $(grep -v '^#' "$ROOT/.env" | xargs)
fi

echo "=== Autopilot Run: $(date) ==="
python3 "$DIR/autopilot.py" "$@"
echo "=== Autopilot Finished: $(date) ==="
