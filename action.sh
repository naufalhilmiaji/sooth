#!/usr/bin/env bash
# Wire SOOTH_* inputs into the sooth CLI, surface the report, propagate the exit code.
# Inputs arrive via env (never interpolated into this script) so untrusted input
# cannot be executed as shell.
set -uo pipefail

args=(--format md)
while IFS= read -r path; do
  [ -z "$path" ] && continue
  args+=(--source "$path")
done <<< "$SOOTH_SOURCE"

args+=(--text "$SOOTH_TEXT")
if [ -n "${SOOTH_CONFIDENCE:-}" ]; then
  args+=(--confidence "$SOOTH_CONFIDENCE")
fi

report="${RUNNER_TEMP:-/tmp}/sooth-report.md"
sooth "${args[@]}" -o "$report"
status=$?

if [ -f "$report" ]; then
  cat "$report"
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    cat "$report" >> "$GITHUB_STEP_SUMMARY"
  fi
fi

exit "$status"
