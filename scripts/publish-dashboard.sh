#!/bin/bash
# Rebuild and push DroneMill Dashboard to GitHub Pages
set -e

ROOT="/home/brewuser/projects/dronemill"
cd "$ROOT"

echo ">> Generating static dashboard data from upload_history and playlists..."
python3 "$ROOT/scripts/build_github_pages.py"

echo ">> Committing and pushing docs/ to GitHub Pages..."
git add docs/
git commit -m "chore(dashboard): update live schedule and telemetry on GitHub Pages" || echo "No changes to commit."
git push origin main

echo "✨ Dashboard published to https://roblanc.github.io/dronemill/"
