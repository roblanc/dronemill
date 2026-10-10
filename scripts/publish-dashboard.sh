#!/bin/bash
# Rebuild and push DroneMill Dashboard to GitHub Pages
set -e
export HOME=/home/brewuser  # dronemill YouTube token lives there

ROOT="/home/brewuser/projects/dronemill"
exec 9>/run/lock/dronemill-pages.lock
flock 9
cd "$ROOT"
# cron runs this as root on a brewuser-owned repo; without this git refuses with "dubious ownership"
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0="$ROOT"

echo ">> Syncing video ids, release times and privacy from YouTube into upload_history..."
python3 "$ROOT/scripts/sync-youtube-ids.py" || echo "WARN: YouTube sync failed, building from the existing history"

echo ">> Generating static dashboard data from upload_history and playlists..."
python3 "$ROOT/scripts/build_github_pages.py"

echo ">> Committing and pushing docs/ to GitHub Pages..."
git add docs/
git commit -m "chore(dashboard): update live schedule and telemetry on GitHub Pages" || echo "No changes to commit."
git push origin main

echo "✨ Dashboard published to https://roblanc.github.io/dronemill/"
