#!/usr/bin/env bash
# Wire SOOTH_* inputs into the sooth CLI, surface the report, emit outputs,
# and apply the fail-on policy. Exit code 0 means the policy was satisfied.
#
# Inputs arrive via env (never interpolated into this script) so untrusted input
# cannot be executed as shell.
set -uo pipefail

workdir="${RUNNER_TEMP:-/tmp}"
report_md="$workdir/sooth-report.md"
report_jsonl="$workdir/sooth-report.jsonl"
: > "$report_jsonl"

args=(--format md --log "$report_jsonl" -o "$report_md")

while IFS= read -r path; do
  [ -z "$path" ] && continue
  args+=(--source "$path")
done <<< "${SOOTH_SOURCE:-}"

args+=(--text "${SOOTH_TEXT:-}")
if [ -n "${SOOTH_CONFIDENCE:-}" ]; then
  args+=(--confidence "$SOOTH_CONFIDENCE")
fi

sooth "${args[@]}"
status=$?

if [ -f "$report_md" ]; then
  cat "$report_md"
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    cat "$report_md" >> "$GITHUB_STEP_SUMMARY"
  fi
fi

# Counts come from the same CLI run — no second API call, no re-parsing of prose.
counts=$(python3 - "$report_jsonl" <<'PY'
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        record = json.loads(fh.readline() or "{}")
except (OSError, ValueError):
    record = {}
tally = {"PASS": 0, "FAIL": 0, "REVIEW": 0, "UNCHECKABLE": 0}
for r in record.get("results", []):
    tally[r.get("kind")] = tally.get(r.get("kind"), 0) + 1
print(f"{tally['PASS']} {tally['FAIL']} {tally['REVIEW']} {tally['UNCHECKABLE']}")
PY
)
if [ -z "$counts" ]; then
  counts="0 0 0 0"
fi
read -r n_pass n_fail n_review n_uncheckable <<< "$counts"

{
  echo "verdicts=PASS $n_pass, FAIL $n_fail, REVIEW $n_review, UNCHECKABLE $n_uncheckable"
  echo "pass-count=$n_pass"
  echo "fail-count=$n_fail"
  echo "review-count=$n_review"
  echo "uncheckable-count=$n_uncheckable"
  echo "report=$report_md"
  echo "exit-code=$status"
} >> "${GITHUB_OUTPUT:-/dev/null}"

if [ ! -f "$report_md" ]; then
  echo "::error::sooth produced no report (CLI exit code $status — check TYPESAFE_API_KEY and the input paths)"
  exit 3
fi

case "${SOOTH_FAIL_ON:-review}" in
  never)
    exit 0
    ;;
  fail)
    # ignore REVIEW (exit 2); still fail the build on a contradiction
    if [ "$status" -eq 2 ]; then
      echo "::warning::sooth found claims needing review, but fail-on is 'fail'"
      exit 0
    fi
    exit "$status"
    ;;
  review|"")
    exit "$status"
    ;;
  *)
    echo "::error::unknown fail-on value '${SOOTH_FAIL_ON}' (expected fail, review, or never)"
    exit 3
    ;;
esac
