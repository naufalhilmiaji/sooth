#!/usr/bin/env bash
# Arg-wiring checks for action.sh. No network — a fake `sooth` records its argv.
# Run: bash tests/test_action.sh
set -uo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

write_fake() {
  cat > "$tmp/sooth" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$ARGV_FILE"
prev=""
for a in "$@"; do
  if [ "$prev" = "-o" ]; then echo "# report" > "$a"; fi
  prev="$a"
done
exit "${FAKE_STATUS:-0}"
EOF
  chmod +x "$tmp/sooth"
}

# argv as one line, plus the same with the dynamic "-o <report>" tail dropped
argv_full() { tr '\n' ' ' < "$ARGV_FILE"; }
args_only() { argv_full | sed 's/ -o [^ ]*//'; }

export PATH="$tmp:$PATH"
export ARGV_FILE="$tmp/argv"
export RUNNER_TEMP="$tmp"
export SOOTH_TEXT="draft.md"
export SOOTH_CONFIDENCE="0.75"
unset GITHUB_STEP_SUMMARY 2>/dev/null || true

fail() { echo "FAIL: $*" >&2; exit 1; }

write_fake

# single source
export SOOTH_SOURCE="policy.md"
bash "$here/../action.sh" >/dev/null || fail "single source: exit $?"
got="$(args_only)"
want="--format md --source policy.md --text draft.md --confidence 0.75 "
[ "$got" = "$want" ] || fail "single source argv: got [$got] want [$want]"

# multiple sources, newline-separated, blanks ignored
export SOOTH_SOURCE="a.md
b.md

c.md"
bash "$here/../action.sh" >/dev/null || fail "multi source: exit $?"
got="$(args_only)"
want="--format md --source a.md --source b.md --source c.md --text draft.md --confidence 0.75 "
[ "$got" = "$want" ] || fail "multi source argv: got [$got] want [$want]"

# confidence is optional
unset SOOTH_CONFIDENCE
export SOOTH_SOURCE="policy.md"
bash "$here/../action.sh" >/dev/null || fail "no confidence: exit $?"
got="$(args_only)"
want="--format md --source policy.md --text draft.md "
[ "$got" = "$want" ] || fail "no confidence argv: got [$got] want [$want]"

# a FAIL from sooth must fail the step (CI gate), and the report still prints
export SOOTH_CONFIDENCE="0.7"
export SOOTH_SOURCE="policy.md"
export FAKE_STATUS=1
out="$(bash "$here/../action.sh")"
status=$?
[ "$status" -eq 1 ] || fail "exit code not propagated: got $status"
[ -n "$out" ] || fail "report not printed on failure"

# hostile input must arrive as a literal argument and never execute
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

echo "ok — action.sh arg wiring (5 checks)"
