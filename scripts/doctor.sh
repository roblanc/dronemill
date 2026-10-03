#!/bin/bash
# Dronemill health check for unattended production.
# Usage:
#   ./scripts/doctor.sh          # tools, creds, disk, dirs
#   ./scripts/doctor.sh --stock  # also require runnable stock/queue

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"

CHECK_STOCK=0
if [ "${1:-}" = "--stock" ]; then
  CHECK_STOCK=1
fi

fail=0
ok() { echo "ok: $*"; }
warn() { echo "warn: $*" >&2; }
bad() { echo "bad: $*" >&2; fail=1; }

need_cmd() {
  if command -v "$1" >/dev/null 2>&1; then
    ok "$1 found"
  else
    bad "$1 missing"
  fi
}

need_cmd ffmpeg
need_cmd ffprobe
need_cmd youtubeuploader
need_cmd python3

if command -v ollama >/dev/null 2>&1; then
  ok "ollama found"
else
  warn "ollama missing; description generation fallback may be limited"
fi

for d in audio audio/queue audio/used images images/queue images/used descriptions output logs state; do
  mkdir -p "$ROOT/$d"
  ok "$d exists"
done

if require_disk_space 10 "$ROOT/output"; then
  ok "disk space >= 10GB"
else
  bad "disk space below render threshold"
fi

CREDS="$HOME/.youtubeuploader/client_secrets.json"
TOKEN="$HOME/.youtubeuploader/request.token"

if [ -f "$CREDS" ]; then
  ok "youtube client_secrets.json found"
else
  bad "youtube client_secrets.json missing at $CREDS"
fi

if [ -f "$TOKEN" ]; then
  ok "youtube request.token found"
else
  bad "youtube request.token missing; first upload would require browser auth"
fi

LOCKFILE="$HOME/.youtubeuploader/upload.lock"
if [ -f "$LOCKFILE" ]; then
  PID=$(cat "$LOCKFILE" 2>/dev/null || true)
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    bad "youtube upload already running, pid=$PID"
  else
    warn "stale upload lock exists: $LOCKFILE"
  fi
else
  ok "no upload lock"
fi

if [ "$CHECK_STOCK" -eq 1 ]; then
  read AUDIO_COUNT IMAGE_COUNT <<< "$(count_queue "$ROOT")"
  QUEUE="$ROOT/queue.csv"
  ROWS=0
  DONE=0
  [ -f "$QUEUE" ] && ROWS=$(python3 - "$QUEUE" <<'PY'
import csv, sys
with open(sys.argv[1], newline="", encoding="utf-8") as f:
    print(sum(1 for r in csv.reader(f) if r and any(x.strip() for x in r)))
PY
)
  [ -f "$ROOT/.batch_state" ] && DONE=$(cat "$ROOT/.batch_state" 2>/dev/null || echo 0)

  if [ "$IMAGE_COUNT" -gt 0 ]; then
    ok "images queued: $IMAGE_COUNT"
  else
    bad "images/queue has no active image files"
  fi

  if [ "$ROWS" -gt "$DONE" ]; then
    ok "queue rows remaining: $((ROWS - DONE))"
  else
    bad "queue.csv has no unprocessed rows"
  fi

  if [ "$AUDIO_COUNT" -gt 0 ]; then
    ok "audio queued: $AUDIO_COUNT"
  else
    warn "audio/queue empty; procedural rows can still run"
  fi
fi

if [ "$fail" -ne 0 ]; then
  echo "doctor: failed" >&2
  exit 1
fi

echo "doctor: ok"
