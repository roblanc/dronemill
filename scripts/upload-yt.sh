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

# YouTube enforces a strict 100-character max limit on video titles
if [ ${#TITLE} -gt 100 ]; then
  echo "WARN: Title exceeds 100 chars (${#TITLE}). Truncating to 100 for YouTube compliance."
  TITLE="${TITLE:0:100}"
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
# systemd jobs run without $HOME set; prefer brewuser home where creds live
if [ -d "/home/brewuser/.youtubeuploader" ]; then
  YT_HOME="/home/brewuser"
else
  YT_HOME="${HOME:-$(getent passwd "$(stat -c %U "$ROOT")" | cut -d: -f6)}"
  [ -z "$YT_HOME" ] || [ "$YT_HOME" = "/" ] && YT_HOME="/home/brewuser"
fi
CREDS="$YT_HOME/.youtubeuploader/client_secrets.json"
TOKEN="$YT_HOME/.youtubeuploader/request.token"
mkdir -p "$YT_HOME/.youtubeuploader"

# Single-instance guard — prevent duplicate uploads
LOCKFILE="$YT_HOME/.youtubeuploader/upload.lock"
if [ -f "$LOCKFILE" ]; then
  PID=$(cat "$LOCKFILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "ERROR: another upload running (PID $PID). Wait for it or kill: kill $PID"
    exit 1
  fi
fi
echo $$ > "$LOCKFILE"
# Preserve exit code on EXIT
trap 'rc=$?; rm -f "$LOCKFILE"; exit $rc' EXIT

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

# Pre-flight token refresh check (fail fast with wizard) — always attempt refresh if refresh_token exists
PRECHECK_LOG=$(mktemp "$YT_HOME/.youtubeuploader/precheck_XXXXXX.log" 2>/dev/null || mktemp /tmp/yt_token_precheck_XXXXXX.log)
python3 <<PYEOF 2>&1 | tee "$PRECHECK_LOG"
import json, sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
TOKEN_PATH="$TOKEN"
CREDS_PATH="$CREDS"
try:
    with open(TOKEN_PATH) as f: t=json.load(f)
    with open(CREDS_PATH) as f: s=json.load(f)
    cfg=s.get("web") or s.get("installed",{})
    creds=Credentials(token=t.get("access_token"), refresh_token=t.get("refresh_token"), token_uri="https://oauth2.googleapis.com/token", client_id=cfg.get("client_id"), client_secret=cfg.get("client_secret"))
    # Always try to refresh to validate token — expiry may be None but token still revoked
    if creds.refresh_token:
        creds.refresh(Request())
        print("TOKEN_OK refreshed")
    else:
        print("TOKEN_OK no refresh needed")
except Exception as e:
    msg=str(e)
    if "invalid_grant" in msg or "expired or revoked" in msg:
        print("TOKEN_INVALID_GRANT:"+msg, file=sys.stderr)
        sys.exit(2)
    print("TOKEN_CHECK_WARN:"+msg, file=sys.stderr)
    sys.exit(0)
PYEOF
PRECHECK_RC=${PIPESTATUS[0]}
rm -f "$PRECHECK_LOG"
if [ $PRECHECK_RC -eq 2 ]; then
  echo "🛑 YouTube OAuth token revoked/expired (invalid_grant)." >&2
  echo "   Your refresh_token from $(date -r "$TOKEN" 2>/dev/null || echo "~/.youtubeuploader/request.token") is no longer valid (Google Testing-mode tokens expire after 7 days of inactivity)." >&2
  echo "   Fix (pick one):" >&2
  echo "   1) Direct on server:  ./scripts/reauth-youtube.sh  (via Chromium :9222, no tunnel, browser opens http://localhost:8080/oauth2callback -> approve @timelessambience55)" >&2
  echo "   2) Or run directly:  $0 \"\$VIDEO\" ...  (same server Chromium flow)" >&2
  echo "   3) See SETUP-YOUTUBE.md section 7 for Desktop-app OAuth re-auth." >&2
  echo "   Keeping local mp4 for retry: $VIDEO" >&2
  VIDEO_ID=""
  AUTH_FAILED=1
else
  UPLOAD_LOG=$(mktemp)
  youtubeuploader \
    -filename "$VIDEO" \
    -title "$TITLE" \
    -description "$DESCRIPTION" \
    -metaJSON "$META" \
    -thumbnail "$THUMB" \
    -secrets "$CREDS" \
    -cache "$TOKEN" 2>&1 | tee "$UPLOAD_LOG"

  if grep -q "invalid_grant" "$UPLOAD_LOG" 2>/dev/null; then
    echo "🛑 Detected invalid_grant during upload — token revoked. See wizard above." >&2
    AUTH_FAILED=1
  else
    AUTH_FAILED=0
  fi

  VIDEO_ID=$(grep -o 'Video ID: [a-zA-Z0-9_-]\+' "$UPLOAD_LOG" | awk '{print $3}' | tail -n 1 || true)
  rm -f "$UPLOAD_LOG"
fi

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

# Auto-enable monetization via YouTube Studio CDP if browser is open
if [ -n "$VIDEO_ID" ] && [ -f "$DIR/set-monetization-studio.js" ]; then
  if curl -s --connect-timeout 2 "http://127.0.0.1:9222/json/version" >/dev/null 2>&1; then
    echo ">> Chrome CDP is active. Auto-enabling monetization in YouTube Studio for $VIDEO_ID..."
    node "$DIR/set-monetization-studio.js" "$VIDEO_ID" || echo "WARN: Monetization activation step failed or skipped."
  fi
fi

# Auto-tag products via YouTube Studio CDP if browser is open
if [ -n "$VIDEO_ID" ] && [ -f "$DIR/tag-products-studio.js" ]; then
  if curl -s --connect-timeout 2 "http://127.0.0.1:9222/json/version" >/dev/null 2>&1; then
    echo ">> Chrome CDP is active. Auto-tagging products in YouTube Studio for $VIDEO_ID..."
    node "$DIR/tag-products-studio.js" "$VIDEO_ID" || echo "WARN: Product auto-tagging step failed or skipped."
  fi
fi

# Clean up local video file ONLY after successful upload (VIDEO_ID exists) to save space
if [ -n "$VIDEO_ID" ] && [ -f "$VIDEO" ]; then
  rm -f "$VIDEO"
  echo "INFO: Deleted local video file after successful upload: $VIDEO to save space."
elif [ -z "$VIDEO_ID" ] && [ -f "$VIDEO" ]; then
  echo "WARN: Upload failed (no VIDEO_ID), keeping local file for retry: $VIDEO"
  if [ "$AUTH_FAILED" = "1" ]; then
    echo "   -> Auth failure: re-run ./scripts/reauth-youtube.sh then retry upload" >&2
  fi
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

# Propagate auth failure to caller (cron will detect and stop refill)
if [ "$AUTH_FAILED" = "1" ]; then
  exit 2
fi
