#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
cd "$ROOT"

SLUG="dronemill"
if [ "${1:-}" != "" ] && [[ "${1:-}" != --* ]]; then
  SLUG="$1"
  shift || true
fi

PROVIDERS="${IMAGE_UI_PROVIDERS:-antigravity,chatgpt}"
had_quota=0
had_unavailable=0
had_failure=0

IFS=',' read -r -a provider_list <<< "$PROVIDERS"
for raw_provider in "${provider_list[@]}"; do
  provider="$(printf '%s' "$raw_provider" | tr '[:upper:]' '[:lower:]' | xargs)"
  [ -n "$provider" ] || continue

  echo "=== UI image provider: $provider ==="
  set +e
  case "$provider" in
    antigravity|gemini|antigravity-gemini)
      node "$DIR/antigravity-image-worker.js" "$SLUG" "$@"
      rc=$?
      ;;
    chatgpt|openai|chatgpt-desktop)
      node "$DIR/chatgpt-image-worker.js" "$SLUG" "$@"
      rc=$?
      ;;
    *)
      echo "WARN: unknown UI image provider '$provider'; skipping"
      rc=3
      ;;
  esac
  set -e

  if [ "$rc" -eq 0 ]; then
    echo "provider $provider completed missing images"
    exit 0
  fi
  if [ "$rc" -eq 2 ]; then
    had_quota=1
    echo "provider $provider quota exhausted; trying next UI provider"
    continue
  fi
  if [ "$rc" -eq 3 ]; then
    had_unavailable=1
    echo "provider $provider unavailable; trying next UI provider"
    continue
  fi

  had_failure=1
  echo "provider $provider failed with exit code $rc; trying next UI provider"
  continue
done

if [ "$had_quota" -eq 1 ]; then
  echo "all available UI providers are quota exhausted"
  exit 2
fi
if [ "$had_unavailable" -eq 1 ]; then
  echo "all configured UI providers are unavailable"
  exit 3
fi
if [ "$had_failure" -eq 1 ]; then
  echo "all configured UI providers failed"
  exit 1
fi

echo "no UI image providers configured"
exit 1
