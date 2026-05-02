#!/bin/bash
# Usage: ./upload-yt.sh <video_path> <title> <desc_file> <thumbnail> [privacy=unlisted]
# Example: ./upload-yt.sh ../output/erebus_v1.mp4 "frozen 169 years..." ../descriptions/erebus_v1.txt ../images/erebus_cover.png

set -e

VIDEO="$1"
TITLE="$2"
DESC="$3"
THUMB="$4"
PRIVACY="${5:-unlisted}"

if [ -z "$VIDEO" ] || [ -z "$TITLE" ] || [ -z "$DESC" ] || [ -z "$THUMB" ]; then
  echo "Usage: $0 <video> <title> <desc_file> <thumbnail> [privacy=unlisted]"
  exit 1
fi

CREDS="$HOME/.youtubeuploader/client_secrets.json"
TOKEN="$HOME/.youtubeuploader/request.token"

if [ ! -f "$CREDS" ]; then
  echo "ERROR: client_secrets.json missing. See SETUP-YOUTUBE.md"
  exit 1
fi

youtubeuploader \
  -filename "$VIDEO" \
  -title "$TITLE" \
  -descriptionFile "$DESC" \
  -categoryId "10" \
  -tags "ambient,cosmic horror,dark ambient,sleep ambient,study music,1 hour ambient,sci-fi ambient,deep space,timeless ambience" \
  -privacy "$PRIVACY" \
  -thumbnail "$THUMB" \
  -secrets "$CREDS" \
  -cache "$TOKEN"

echo "Uploaded: $TITLE"
