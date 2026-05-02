#!/bin/bash
# shared helpers

slugify() {
  # Converts: "frozen 169 years | hms erebus deep ambient" -> "frozen-169-years-hms-erebus-deep-ambient"
  echo "$1" | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g' \
    | sed -E 's/^-+|-+$//g' \
    | cut -c1-80
}

next_image() {
  # Returns oldest image in images/queue/ (alphabetical)
  local DIR="$1"
  local IMG
  IMG=$(find "$DIR/images/queue" -maxdepth 1 \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \) -type f 2>/dev/null | sort | head -1)
  if [ -z "$IMG" ]; then
    echo "ERROR: no images in $DIR/images/queue/" >&2
    return 1
  fi
  echo "$IMG"
}

mark_used() {
  # Move image from queue/ to used/
  local IMG="$1"
  local DIR="$2"
  mv "$IMG" "$DIR/images/used/"
}
