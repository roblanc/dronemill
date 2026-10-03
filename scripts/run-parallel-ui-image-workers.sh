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

PROMPTS="output/ui_image_prompts.txt"
PROVIDERS="antigravity,chatgpt"
MODE="alternate"
OUT_DIR="output/parallel-ui-prompts"
PASS_ARGS=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    --prompts)
      PROMPTS="${2:-}"
      shift 2
      ;;
    --providers)
      PROVIDERS="${2:-}"
      shift 2
      ;;
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="${2:-}"
      shift 2
      ;;
    *)
      PASS_ARGS+=("$1")
      shift
      ;;
  esac
done

SPLIT_CMD=(python3 "$DIR/split-ui-image-prompts.py" "$SLUG" --providers "$PROVIDERS" --mode "$MODE")
if [ -n "$PROMPTS" ]; then
  SPLIT_CMD+=(--prompts "$PROMPTS")
fi
if [ -n "$OUT_DIR" ]; then
  SPLIT_CMD+=(--out-dir "$OUT_DIR")
fi

split_output="$("${SPLIT_CMD[@]}")"
printf '%s\n' "$split_output"

provider_lines=()
while IFS= read -r line; do
  provider_lines+=("$line")
done < <(printf '%s\n' "$split_output" | awk '/ prompts=/{print}')
if [ "${#provider_lines[@]}" -eq 0 ]; then
  echo "ERROR: split produced no provider batches" >&2
  exit 1
fi

declare -a pids=()
declare -a pid_providers=()
declare -a pid_files=()

for line in "${provider_lines[@]}"; do
  provider="${line%% prompts=*}"
  prompt_file="${line##* file=}"
  if [[ ! -s "$prompt_file" ]]; then
    echo "Skipping $provider because prompt file is empty: $prompt_file"
    continue
  fi

  echo "=== parallel UI image provider: $provider ==="
  if [ "${#PASS_ARGS[@]}" -gt 0 ]; then
    IMAGE_UI_PROVIDERS="$provider" "$DIR/ui-image-worker.sh" "$SLUG" --prompts "$prompt_file" "${PASS_ARGS[@]}" &
  else
    IMAGE_UI_PROVIDERS="$provider" "$DIR/ui-image-worker.sh" "$SLUG" --prompts "$prompt_file" &
  fi
  pids+=("$!")
  pid_providers+=("$provider")
  pid_files+=("$prompt_file")
done

if [ "${#pids[@]}" -eq 0 ]; then
  echo "No provider runs started."
  exit 0
fi

overall_rc=0
had_quota=0
had_unavailable=0

for idx in "${!pids[@]}"; do
  pid="${pids[$idx]}"
  provider="${pid_providers[$idx]}"
  prompt_file="${pid_files[$idx]}"
  rc=0
  if wait "$pid"; then
    echo "provider $provider completed batch from $prompt_file"
    continue
  else
    rc=$?
  fi

  echo "provider $provider exited with code $rc"
  if [ "$rc" -eq 2 ]; then
    had_quota=1
  elif [ "$rc" -eq 3 ]; then
    had_unavailable=1
  else
    overall_rc=1
  fi
done

if [ "$overall_rc" -ne 0 ]; then
  exit 1
fi
if [ "$had_quota" -eq 1 ]; then
  exit 2
fi
if [ "$had_unavailable" -eq 1 ]; then
  exit 3
fi

exit 0
