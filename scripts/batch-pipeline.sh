#!/bin/bash
# Batch process N videos from the queue.
# Usage: ./batch-pipeline.sh <count> <desc_file> [pitch]
# Example: ./batch-pipeline.sh 5 ../descriptions/default.txt

COUNT=$1
DESC=$2
PITCH=${3:-0.93}

if [ -z "$COUNT" ] || [ -z "$DESC" ]; then
  echo "Usage: $0 <count> <desc_file> [pitch]"
  exit 1
fi

DIR="$(cd "$(dirname "$0")" && pwd)"

for i in $(seq 1 $COUNT); do
  echo ""
  echo "========================================"
  echo "PROCESSING VIDEO $i OF $COUNT"
  echo "========================================"
  
  "$DIR/full-pipeline.sh" "auto" "auto" "$DESC" "$PITCH" "schedule"
  
  if [ $? -ne 0 ]; then
    echo "Batch failed at video $i. Stopping."
    exit 1
  fi
done

echo ""
echo "Batch completed successfully!"
