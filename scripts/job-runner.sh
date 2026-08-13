#!/bin/bash
# Run and manage DroneMill commands independently of SSH or OpenCode.
# Usage:
#   ./scripts/job-runner.sh start <name> -- <command> [args...]
#   ./scripts/job-runner.sh status <name>
#   ./scripts/job-runner.sh list
#   ./scripts/job-runner.sh logs <name> [lines=80]
#   ./scripts/job-runner.sh stop <name>

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
STATE_ROOT="${DRONEMILL_JOB_DIR:-/var/lib/dronemill/jobs}"
ACTION="${1:-}"
NAME="${2:-}"

slugify_job() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//'
}

require_name() {
  if [ -z "$NAME" ]; then
    echo "ERROR: job name required" >&2
    exit 2
  fi
}

unit_for() {
  printf 'dronemill-job-%s.service' "$(slugify_job "$1")"
}

job_dir_for() {
  printf '%s/%s' "$STATE_ROOT" "$(slugify_job "$1")"
}

case "$ACTION" in
  start)
    require_name
    shift 2
    [ "${1:-}" = "--" ] && shift
    if [ "$#" -eq 0 ]; then
      echo "Usage: $0 start <name> -- <command> [args...]" >&2
      exit 2
    fi

    mkdir -p "$STATE_ROOT"
    JOB_DIR="$(job_dir_for "$NAME")"
    UNIT="$(unit_for "$NAME")"
    if systemctl is-active --quiet "$UNIT"; then
      echo "ERROR: job already running: $NAME" >&2
      exit 1
    fi

    mkdir -p "$JOB_DIR"
    rm -f "$JOB_DIR/exit_code" "$JOB_DIR/finished_at"
    printf '%s\n' "$NAME" > "$JOB_DIR/name"
    printf '%s\n' "$UNIT" > "$JOB_DIR/unit"
    printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$JOB_DIR/queued_at"
    printf 'queued\n' > "$JOB_DIR/status"
    printf '%q ' "$@" > "$JOB_DIR/command"
    printf '\n' >> "$JOB_DIR/command"
    : > "$JOB_DIR/job.log"

    systemd-run \
      --unit="$UNIT" \
      --description="DroneMill job: $NAME" \
      --service-type=exec \
      --property="WorkingDirectory=$ROOT" \
      --property="StandardOutput=append:$JOB_DIR/job.log" \
      --property="StandardError=append:$JOB_DIR/job.log" \
      --property="Nice=10" \
      --property="IOSchedulingClass=best-effort" \
      --property="IOSchedulingPriority=6" \
      "$DIR/job-worker.sh" "$JOB_DIR" "$@"

    echo "Started: $NAME"
    echo "Unit:    $UNIT"
    echo "Status:  $0 status '$NAME'"
    echo "Logs:    $0 logs '$NAME'"
    ;;
  status)
    require_name
    JOB_DIR="$(job_dir_for "$NAME")"
    UNIT="$(unit_for "$NAME")"
    if [ ! -d "$JOB_DIR" ]; then
      echo "ERROR: unknown job: $NAME" >&2
      exit 1
    fi
    echo "Name:     $(cat "$JOB_DIR/name")"
    echo "Status:   $(cat "$JOB_DIR/status")"
    echo "Unit:     $UNIT"
    echo "Active:   $(systemctl is-active "$UNIT" 2>/dev/null || true)"
    [ -f "$JOB_DIR/queued_at" ] && echo "Queued:   $(cat "$JOB_DIR/queued_at")"
    [ -f "$JOB_DIR/started_at" ] && echo "Started:  $(cat "$JOB_DIR/started_at")"
    [ -f "$JOB_DIR/finished_at" ] && echo "Finished: $(cat "$JOB_DIR/finished_at")"
    [ -f "$JOB_DIR/exit_code" ] && echo "Exit:     $(cat "$JOB_DIR/exit_code")"
    echo "Command:  $(cat "$JOB_DIR/command")"
    echo "Log:      $JOB_DIR/job.log"
    ;;
  list)
    if [ ! -d "$STATE_ROOT" ]; then
      echo "No jobs."
      exit 0
    fi
    printf '%-32s %-12s %-20s\n' NAME STATUS STARTED
    for JOB_DIR in "$STATE_ROOT"/*; do
      [ -d "$JOB_DIR" ] || continue
      JOB_NAME="$(cat "$JOB_DIR/name" 2>/dev/null || basename "$JOB_DIR")"
      STATUS="$(cat "$JOB_DIR/status" 2>/dev/null || echo unknown)"
      STARTED="$(cat "$JOB_DIR/started_at" 2>/dev/null || echo '-')"
      printf '%-32s %-12s %-20s\n' "$JOB_NAME" "$STATUS" "$STARTED"
    done
    ;;
  logs)
    require_name
    JOB_DIR="$(job_dir_for "$NAME")"
    LINES="${3:-80}"
    if [ ! -f "$JOB_DIR/job.log" ]; then
      echo "ERROR: no log for job: $NAME" >&2
      exit 1
    fi
    tail -n "$LINES" "$JOB_DIR/job.log"
    ;;
  stop)
    require_name
    JOB_DIR="$(job_dir_for "$NAME")"
    UNIT="$(unit_for "$NAME")"
    systemctl stop "$UNIT"
    printf 'stopped\n' > "$JOB_DIR/status"
    date -u +%Y-%m-%dT%H:%M:%SZ > "$JOB_DIR/finished_at"
    echo "Stopped: $NAME"
    ;;
  *)
    echo "Usage: $0 {start <name> -- <command...>|status <name>|list|logs <name> [lines]|stop <name>}" >&2
    exit 2
    ;;
esac
