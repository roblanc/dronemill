#!/bin/bash
# Wizard to re-authenticate YouTube OAuth for Dronemill
# Handles invalid_grant after Testing-mode expiry
set -e
YT_HOME="/home/brewuser"
CREDS="$YT_HOME/.youtubeuploader/client_secrets.json"
TOKEN="$YT_HOME/.youtubeuploader/request.token"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Dronemill YouTube Re-Auth Wizard ==="
echo "Channel: @timelessambience55"
echo "Project: timeless-ambience-uploader"
echo ""

if [ ! -f "$CREDS" ]; then
  echo "ERROR: $CREDS missing. See SETUP-YOUTUBE.md"
  exit 1
fi

echo "Current token: $TOKEN"
if [ -f "$TOKEN" ]; then
  echo "  Last modified: $(date -r "$TOKEN")"
  python3 <<PY 2>&1 | head -n 20
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
try:
    import json as j
    with open("$TOKEN") as f: t=j.load(f)
    with open("$CREDS") as f: s=j.load(f)
    cfg=s.get("web") or s.get("installed",{})
    c=Credentials(token=t.get("access_token"), refresh_token=t.get("refresh_token"), token_uri="https://oauth2.googleapis.com/token", client_id=cfg.get("client_id"), client_secret=cfg.get("client_secret"))
    if c.expired and c.refresh_token:
        c.refresh(Request())
    print("TOKEN_OK: still valid")
except Exception as e:
    print(f"TOKEN_STATUS: {e}")
PY
else
  echo "  No token file yet"
fi

echo ""
echo "Google Testing-mode tokens expire after 7 days of inactivity."
echo "Your refresh_token was revoked (invalid_grant)."
echo ""
echo "Choose re-auth method:"
echo "  [1] Direct on server via Chromium (headless, no tunnel - recommended)"
echo "  [2] Local machine (copy client_secrets.json)"
echo "  [3] Show manual URL"
echo ""
read -p "Choice [1/2/3]: " choice

if [ "$choice" = "1" ]; then
  echo ""
  echo "Running directly on server via Chromium (CDP http://localhost:9222) - no SSH tunnel needed."
  echo "  youtubeuploader will listen on http://localhost:8080/oauth2callback"
  echo "  and open OAuth URL in the server's Chromium (remote-debugging-port 9222)."
  echo ""
  echo "  Test upload that triggers browser flow:"
  echo "  $ROOT/scripts/upload-yt.sh $ROOT/output/dronemill-private-test-10s.mp4 \"test auth\" $ROOT/descriptions/template.txt $ROOT/images/used/001_erebus.png private"
  echo ""
  echo "  (If no test video, create one: ffmpeg -f lavfi -i color=c=black:s=1280x720:d=5 -pix_fmt yuv420p /tmp/test.mp4)"
  echo ""
  echo "Browser will open http://localhost:8080/oauth2callback -> approve Google account that owns @timelessambience55"
  echo "Token will be saved to $TOKEN"
  echo ""
  read -p "Press Enter when ready to try test upload now? [y/N] " yn
  if [ "$yn" = "y" ]; then
    TMPVID="/tmp/dronemill_reauth_test.mp4"
    if [ ! -f "$TMPVID" ]; then
      ffmpeg -y -f lavfi -i "color=c=black:s=1280x720:d=3:r=24" -pix_fmt yuv420p -t 3 "$TMPVID" 2>/dev/null
    fi
    echo "Launching youtubeuploader auth flow..."
    youtubeuploader -filename "$TMPVID" -title "reauth test $(date +%s)" -description "reauth test" -secrets "$CREDS" -cache "$TOKEN" || true
    echo "Check $TOKEN"
    ls -lh "$TOKEN"
  fi

elif [ "$choice" = "2" ]; then
  echo ""
  echo "On LOCAL MACHINE:"
  echo "  1. scp brewuser@$(hostname -f):$CREDS ./client_secrets.json"
  echo "  2. brew install youtubeuploader  (or go install github.com/Porjo/youtubeuploader)"
  echo "  3. youtubeuploader -filename /tmp/test.mp4 -title test -secrets ./client_secrets.json -cache ./request.token"
  echo "     -> browser flow -> approve"
  echo "  4. scp ./request.token brewuser@$(hostname -f):$TOKEN"
  echo "  5. Verify: python3 -c \"from google.oauth2.credentials import Credentials; ...\" "

elif [ "$choice" = "3" ]; then
  CLIENT_ID=$(python3 -c "import json; print(json.load(open('$CREDS'))['web']['client_id'])")
  echo ""
  echo "Manual OAuth URL (open in browser logged into owner of @timelessambience55):"
  echo "https://accounts.google.com/o/oauth2/auth?access_type=offline&client_id=$CLIENT_ID&prompt=consent&redirect_uri=http://localhost:8080/oauth2callback&response_type=code&scope=https://www.googleapis.com/auth/youtube.upload%20https://www.googleapis.com/auth/youtube"
  echo ""
  echo "After consent, google redirects to http://localhost:8080/oauth2callback?code=XXXX"
  echo "youtubeuploader handles code exchange automatically if listening on :8080."
  echo "Just run youtubeuploader directly on server - Chromium on :9222 handles the callback, no tunnel."
fi

echo ""
echo "After re-auth, verify:"
echo "  python3 $ROOT/scripts/cron_weekly_buffer.py  # should show Buffer refill and upload"
echo "  ls -lh $ROOT/output/*.mp4"
