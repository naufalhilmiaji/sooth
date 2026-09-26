#!/usr/bin/env bash
# Live smoke against Jev. Requires TYPESAFE_API_KEY and the typesafe-sdk.
# Not run in unit CI — it costs money and would fail on forks without a key.
#
# Usage:  bash tests/smoke.sh          (uses an active venv, then ./.venv, then python3)
#         PYTHON=/path/to/python bash tests/smoke.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src

# The SDK lives in the project venv, not necessarily in the system interpreter.
if [ -n "${PYTHON:-}" ]; then
  py="$PYTHON"
elif [ -x .venv/bin/python ]; then
  py=".venv/bin/python"
else
  py="python3"
fi

if [ -z "${TYPESAFE_API_KEY:-}" ]; then
  echo "smoke skipped: TYPESAFE_API_KEY is not set (get one at console.typesafe.ai)" >&2
  exit 3
fi
if ! "$py" -c "import typesafe_sdk" >/dev/null 2>&1; then
  echo "smoke FAILED: typesafe-sdk not importable by $py" >&2
  echo "  fix: pip install -e \".[dev]\"  — or point PYTHON at the right interpreter" >&2
  exit 3
fi

echo "== hero fixture: release notes vs AI summary (3 planted numeric FAILs, must exit 1)"
set +e
"$py" -m sooth.cli \
  --source examples/release-notes.md \
  --text examples/ai-summary.md \
  --format json -o /tmp/sooth-smoke.json \
  --log /tmp/sooth-smoke.jsonl >/dev/null
hero_code=$?
set -e
if [ "$hero_code" -ne 1 ]; then
  echo "smoke FAILED: hero draft exit=$hero_code, want 1 (drop -o to see the report)" >&2
  exit 1
fi
"$py" - <<'PY'
import json
report = json.load(open("/tmp/sooth-smoke.json"))
s = report["summary"]
assert report["exit_code"] == 1, s
assert (s["pass"], s["fail"], s["uncheckable"]) == (4, 3, 1), s
# every FAIL must carry the source span it was judged against
for v in report["verdicts"]:
    if v["kind"] == "FAIL":
        assert v["evidence"], f"FAIL without evidence: {v['text']}"
print(f"  hero json ok: {s}")
PY

echo "== honest summary (fixture sanity, exit <3 ok)"
set +e
"$py" -m sooth.cli \
  --source examples/news-1.md \
  --text examples/news-1-summ.md \
  --log /tmp/sooth-smoke.jsonl >/dev/null
summ_code=$?
set -e
if [ "$summ_code" -ge 3 ]; then
  echo "smoke FAILED: summ exit=$summ_code (want 0-2)" >&2
  exit 1
fi

echo "== evil draft (planted FAILs, must exit 1)"
set +e
"$py" -m sooth.cli \
  --source examples/news-1.md \
  --text examples/news-1-evil.md \
  --log /tmp/sooth-smoke.jsonl
code=$?
set -e
if [ "$code" -ne 1 ]; then
  echo "smoke FAILED: evil draft exit=$code, want 1" >&2
  exit 1
fi
echo "smoke ok (log: /tmp/sooth-smoke.jsonl)"
