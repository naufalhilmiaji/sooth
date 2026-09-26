#!/usr/bin/env bash
# Arg-wiring and fail-on policy checks for action.sh.
# No network — a fake `sooth` records its argv, writes a stub report and a stub log.
# Run: bash tests/test_action.sh
set -uo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

LOG_ONE_FAIL='{"results":[{"kind":"PASS"},{"kind":"FAIL"},{"kind":"UNCHECKABLE"}]}'
LOG_REVIEW_ONLY='{"results":[{"kind":"PASS"},{"kind":"REVIEW"}]}'

write_fake() {
  cat > "$tmp/sooth" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$ARGV_FILE"
prev=""
for a in "$@"; do
  if [ "$prev" = "-o" ]; then echo "# report" > "$a"; fi
  if [ "$prev" = "--log" ]; then printf '%s\n' "${FAKE_LOG:-\{\}}" > "$a"; fi
  prev="$a"
done
exit "${FAKE_STATUS:-0}"
EOF
  chmod +x "$tmp/sooth"
}

# argv as one line, minus the dynamic report/log paths
argv_full() { tr '\n' ' ' < "$ARGV_FILE"; }
args_only() { argv_full | sed -e 's/ --log [^ ]*//' -e 's/ -o [^ ]*//'; }
outputs() { cat "$GITHUB_OUTPUT"; }

export PATH="$tmp:$PATH"
export ARGV_FILE="$tmp/argv"
export RUNNER_TEMP="$tmp"
export GITHUB_OUTPUT="$tmp/gh_output"
export SOOTH_TEXT="draft.md"
export SOOTH_CONFIDENCE="0.75"
unset GITHUB_STEP_SUMMARY 2>/dev/null || true

fail() { echo "FAIL: $*" >&2; exit 1; }

write_fake

# --- arg wiring -------------------------------------------------------------

export SOOTH_SOURCE="policy.md"
bash "$here/../action.sh" >/dev/null || fail "single source: exit $?"
got="$(args_only)"
want="--format md --source policy.md --text draft.md --confidence 0.75 "
[ "$got" = "$want" ] || fail "single source argv: got [$got] want [$want]"
case "$(argv_full)" in
  *"--log $tmp/sooth-report.jsonl -o $tmp/sooth-report.md"*) : ;;
  *) fail "report and log go to RUNNER_TEMP: [$(argv_full)]" ;;
esac

export SOOTH_SOURCE="a.md
b.md

c.md"
bash "$here/../action.sh" >/dev/null || fail "multi source: exit $?"
got="$(args_only)"
want="--format md --source a.md --source b.md --source c.md --text draft.md --confidence 0.75 "
[ "$got" = "$want" ] || fail "multi source argv: got [$got] want [$want]"

unset SOOTH_CONFIDENCE
export SOOTH_SOURCE="policy.md"
bash "$here/../action.sh" >/dev/null || fail "no confidence: exit $?"
got="$(args_only)"
want="--format md --source policy.md --text draft.md "
[ "$got" = "$want" ] || fail "no confidence argv: got [$got] want [$want]"
export SOOTH_CONFIDENCE="0.7"

# --- outputs ----------------------------------------------------------------

export FAKE_STATUS=1
export FAKE_LOG="$LOG_ONE_FAIL"
bash "$here/../action.sh" >/dev/null
out="$(outputs)"
case "$out" in
  *"verdicts=PASS 1, FAIL 1, REVIEW 0, UNCHECKABLE 1"*) : ;;
  *) fail "verdicts output: [$out]" ;;
esac
case "$out" in
  *"fail-count=1"*) : ;;
  *) fail "fail-count output: [$out]" ;;
esac
case "$out" in
  *"exit-code=1"*) : ;;
  *) fail "exit-code output: [$out]" ;;
esac

# --- fail-on policy ---------------------------------------------------------

# default (review): a FAIL fails the step, and the report still prints
out="$(bash "$here/../action.sh")"
status=$?
[ "$status" -eq 1 ] || fail "review default did not propagate FAIL: got $status"
[ -n "$out" ] || fail "report not printed on failure"

# fail-on=fail: REVIEW-only run must not fail the step
export SOOTH_FAIL_ON="fail"
export FAKE_STATUS=2
export FAKE_LOG="$LOG_REVIEW_ONLY"
bash "$here/../action.sh" >/dev/null 2>&1
status=$?
[ "$status" -eq 0 ] || fail "fail-on=fail should tolerate REVIEW: got $status"

# fail-on=fail: FAIL still fails the step
export FAKE_STATUS=1
export FAKE_LOG="$LOG_ONE_FAIL"
bash "$here/../action.sh" >/dev/null 2>&1
status=$?
[ "$status" -eq 1 ] || fail "fail-on=fail must propagate FAIL: got $status"

# fail-on=never: nothing fails the step
export SOOTH_FAIL_ON="never"
export FAKE_STATUS=1
bash "$here/../action.sh" >/dev/null 2>&1
status=$?
[ "$status" -eq 0 ] || fail "fail-on=never should always pass: got $status"

# fail-on=<garbage> is a config error
export SOOTH_FAIL_ON="sometimes"
export FAKE_STATUS=0
bash "$here/../action.sh" >/dev/null 2>&1
status=$?
[ "$status" -eq 3 ] || fail "unknown fail-on should exit 3: got $status"
unset SOOTH_FAIL_ON

# --- hostile input ----------------------------------------------------------

export FAKE_STATUS=0
export SOOTH_TEXT='draft.md; echo PWNED'
out="$(bash "$here/../action.sh")" || fail "injection: exit $?"
case "$out" in
  *PWNED*) fail "input was executed as shell" ;;
esac
full="$(argv_full)"
case "$full" in
  *"--text draft.md; echo PWNED "*) : ;;
  *) fail "injection argv: got [$full]" ;;
esac

echo "ok — action.sh arg wiring, outputs, fail-on policy (11 checks)"
