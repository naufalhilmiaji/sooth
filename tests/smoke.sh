#!/usr/bin/env bash
# Live smoke against Jev. Requires TYPESAFE_API_KEY. Not run in unit CI.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src

echo "== honest summary (fixture sanity, any report ok)"
python3 -m sooth.cli \
  --source examples/news-1.md \
  --text examples/news-1-summ.md \
  --log /tmp/sooth-smoke.jsonl >/dev/null

echo "== evil draft (planted FAILs, must exit 1)"
set +e
python3 -m sooth.cli \
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
