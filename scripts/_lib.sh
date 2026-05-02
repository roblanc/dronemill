#!/bin/bash
# shared helpers

slugify() {
  # Converts: "He Was Already Waiting Behind the Door…" -> "he-was-already-waiting-behind-the-door"
  echo "$1" | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g' \
    | sed -E 's/^-+|-+$//g' \
    | cut -c1-80
}

next_image() {
  local DIR="$1"
  local IMG
  IMG=$(find "$DIR/images/queue" -maxdepth 1 \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \) -type f 2>/dev/null | sort | head -1)
  if [ -z "$IMG" ]; then
    echo "ERROR: no images in $DIR/images/queue/" >&2
    return 1
  fi
  echo "$IMG"
}

next_audio() {
  local DIR="$1"
  local AUD
  AUD=$(find "$DIR/audio/queue" -maxdepth 1 \( -name "*.mp3" -o -name "*.wav" -o -name "*.flac" -o -name "*.m4a" \) -type f 2>/dev/null | sort | head -1)
  if [ -z "$AUD" ]; then
    echo "ERROR: no audio in $DIR/audio/queue/" >&2
    return 1
  fi
  echo "$AUD"
}

mark_image_used() {
  local IMG="$1"
  local DIR="$2"
  mv "$IMG" "$DIR/images/used/"
}

mark_audio_used() {
  local AUD="$1"
  local DIR="$2"
  mv "$AUD" "$DIR/audio/used/"
}

# Backward-compat alias
mark_used() { mark_image_used "$@"; }

count_queue() {
  # Returns: <audio_count> <image_count>
  local DIR="$1"
  local A I
  A=$(find "$DIR/audio/queue" -maxdepth 1 \( -name "*.mp3" -o -name "*.wav" -o -name "*.flac" -o -name "*.m4a" \) -type f 2>/dev/null | wc -l | xargs)
  I=$(find "$DIR/images/queue" -maxdepth 1 \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \) -type f 2>/dev/null | wc -l | xargs)
  echo "$A $I"
}
