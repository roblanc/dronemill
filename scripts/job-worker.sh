#!/bin/bash
# Internal worker launched by job-runner.sh through the system systemd manager.

set -uo pipefail

JOB_DIR="${1:-}"
shift || true

if [ -z "$JOB_DIR" ] || [ "$#" -eq 0 ]; then
  echo "Usage: $0 <job_dir> <command> [args...]" >&2
  exit 2
fi

write_state() {
  printf '%s\n' "$1" > "$JOB_DIR/status"
}

mkdir -p "$JOB_DIR"
date -u +%Y-%m-%dT%H:%M:%SZ > "$JOB_DIR/started_at"
write_state running

"$@"
EXIT_CODE=$?

printf '%s\n' "$EXIT_CODE" > "$JOB_DIR/exit_code"
date -u +%Y-%m-%dT%H:%M:%SZ > "$JOB_DIR/finished_at"
if [ "$EXIT_CODE" -eq 0 ]; then
  write_state completed
else
  write_state failed
fi

exit "$EXIT_CODE"
