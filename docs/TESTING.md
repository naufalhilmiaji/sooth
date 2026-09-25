# Tests & Verification Plan — Sooth v0.1

Three layers: fast pure checks (always), live API smoke (optional), accuracy calibration (human, before release). Matches `DESIGN.md` module split.

## 1. Unit / pure checks — `tests/test_core.py`

One file, plain asserts, run with `python -m tests.test_core` or pytest if already installed. No network. Covers the logic that would silently corrupt verdicts:

| Area | Cases (assert each) |
|------|---------------------|
| `claims.split` | sentence boundaries; `3.5 days` stays one claim; headings skipped; `?` lines skipped; `< 4` words skipped; `draft_line` correct |
| verdict mapping | checkable<0.5 → UNCHECKABLE; low confidence → REVIEW; supports/contradicts/not_found → PASS/FAIL/REVIEW at high confidence; threshold boundary inclusive |
| `report.render` | counts line correct; every claim appears once; bar length ∝ probability; empty verdicts list → still prints summary |
| log writer | one JSON line per run; round-trips `json.loads`; no `api_key` field anywhere |

Entry bar: `python -m tests.test_core` exits 0 on a clean tree. This is the one runnable check left behind with the code.

## 2. Live smoke (optional, real key)

- Fixture `examples/`: `source.md` (short policy: refunds in 3 days, card-and-bank only), `draft.md` (3 claims: one supported, one contradicted, one fluff).
- `sooth --source examples/source.md --text examples/draft.md`
- Pass when: process exits with code matching expected verdicts (1 FAIL present → exit 1), report table has 3 rows, `--log /tmp/t.jsonl` has exactly 1 line with `model` = pinned version.
- Script it as `tests/smoke.sh` (5 lines). Not run in unit CI. Skip entirely when `TYPESAFE_API_KEY` unset.

## 3. Accuracy calibration (live, labeled set)

Goal from PRD: ≥ 24/30 correct on a labeled set, zero confident-wrong `PASS` on contradicted claims.

- Labeled set: `examples/calibration.json` — 30 claims across `news-1.md`, `policy.md`, `pricing.md` (10 supported / 10 contradicted / 10 absent-or-opinion, each with an `expected` verdict and a note).
- Runner: `PYTHONPATH=src python3 tests/calibrate.py [--confidence T]` — batches live Jev calls, prints the confusion matrix, exits 0 only when the bar is met.
- Frozen matrix + notes: `examples/calibration.md` (threshold 0.7, `jev-1.13.0`, 30/30).
- Never move the threshold to hide a confident-wrong `PASS` — fix question wording instead (`instructions`/`criteria` in `verify.py`). Bump model version → re-run this layer.

## 4. Manual UX check (10 min)

- [ ] `sooth --help` alone explains enough to run.
- [ ] Report readable by someone who never saw the tool (show one person).
- [ ] Missing key → one-line hint mentioning `TYPESAFE_API_KEY`, exit 3, no stack trace.
- [ ] Exit codes: all-PASS fixture → 0; with-REVIEW fixture → 2; with-FAIL → 1.

## 5. Definition of done (v0.1)

1. `tests/test_core.py` green.
2. Smoke fixture behaves (§2) with a real key at least once.
3. Calibration table recorded (§3) and default threshold justified by it.
4. Manual checklist (§4) done.
5. Docs match reality: report column that shows probability distribution (not source snippets) — snippets deferred to v0.2 per `DESIGN.md`.

## Out of scope for testing now

Load/perf (CLI is one-shot), fuzzing, multi-language accuracy, regression CI on live API (costs money; add when thresholds ship to users).
