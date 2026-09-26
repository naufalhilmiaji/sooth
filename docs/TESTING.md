# Tests & Verification Plan — Sooth v0.1

Three layers: fast pure checks (always), live API smoke (optional), accuracy calibration (human, before release). Matches `DESIGN.md` module split.

## 1. Unit / pure checks — `tests/test_core.py`

One file, plain asserts, run with `python -m tests.test_core` or pytest if already installed. No network. Covers the logic that would silently corrupt verdicts:

| Area | Cases (assert each) |
|------|---------------------|
| `claims.split` | sentence boundaries; `3.5 days` stays one claim; headings skipped; `?` lines skipped; `< 4` words skipped; `draft_line` correct |
| verdict mapping | checkable<0.5 → UNCHECKABLE; low confidence → REVIEW; supports/contradicts/not_found → PASS/FAIL/REVIEW at high confidence; threshold boundary inclusive |
| `report.render_markdown` | counts line correct; every claim appears once; bar length ∝ probability; empty verdicts list → still prints summary |
| `report.render_json` | summary counts and `threshold`; `exit_code` equals `exit_code(verdicts)`; verdict order and keys; `missing_numbers` and `evidence` (`null` when none); no `api_key` anywhere |
| JSON surface agreement | `log_record(...)["results"] == render_json(...)["verdicts"]` — the two JSON surfaces cannot drift |
| version guard | `sooth.__version__` is either the `pyproject.toml` version or the source-tree sentinel; fails on a stale hardcoded literal |
| demo fixtures | every `DEMO_CASES` entry points at a real file; valid JSON; non-empty results; threshold in (0,1); model pinned to `jev-*`; every `kind` in the fixed vocabulary; `verdicts_from_record` round-trips |
| CLI surface | `main(["demo", "--case", <every case>])` renders to stdout with no network and returns a valid exit code; `--format json` output parses and agrees with the returned code; missing `--source`/`--text` → 3; `--version` exits 0 and prints `sooth <version>`; `RENDERERS` covers `md|plain|json` |
| log writer | one JSON line per run; round-trips `json.loads`; no `api_key` field anywhere |

Entry bar: `python3 tests/test_core.py` exits 0 on a clean tree. This is the one runnable check
left behind with the code. `pytest` runs the same functions.

## 1b. GitHub Action checks — `tests/test_action.sh`

No network. A fake `sooth` on `PATH` records its argv and writes stub report and log files, so
arg wiring and policy can be asserted without an API key.

| Case | Asserts |
|------|---------|
| arg wiring | single source; multi-source split on newlines with blanks dropped; `--confidence` optional; report and log paths land under `RUNNER_TEMP` |
| outputs | `verdicts`, `fail-count`, `exit-code` written to `GITHUB_OUTPUT`, derived from the same CLI run |
| `fail-on=review` (default) | exit 1 propagates; report still prints |
| `fail-on=fail` | REVIEW-only run (exit 2) passes; FAIL run (exit 1) still fails |
| `fail-on=never` | nothing fails the step |
| `fail-on=<garbage>` | exits 3 rather than silently passing or failing |
| hostile input | `draft.md; echo PWNED` arrives as a literal argv entry and is never executed |

## 2. Live smoke (optional, real key)

Two fixtures, both in `examples/`:

- **Hero set** — `release-notes.md` (a product release note) vs `ai-summary.md` (an AI summary with three numbers quietly wrong). Expected: `PASS 4 · FAIL 3 · UNCHECKABLE 1`, exit 1. Run it with `--log` and diff the report against the bundled `src/sooth/demo-en.json` record; a divergence means the model version or the questions moved.
- **Minimal set** — `source.md` (short policy: refunds in 3 days, card-and-bank only) vs `draft.md` (3 claims: one supported, one contradicted, one fluff). Expected: `PASS 1 · FAIL 1 · UNCHECKABLE 1`, exit 1, report table has 3 rows.

- Pass when: the process exits with the code the verdicts imply, the table has the expected row count, and `--log /tmp/t.jsonl` has exactly 1 line per run with `model` = the pinned version.
- Scripted as `tests/smoke.sh`. Not run in unit CI — it costs money and would break on forks without a key. Skip entirely when `TYPESAFE_API_KEY` is unset.

Offline equivalents that *do* run in CI: `sooth demo` and `sooth demo --case id` replay the
recorded runs and assert the documented exit codes. If a live smoke run disagrees with a demo
record, the record is stale — re-record it (see `CONTRIBUTING.md`) rather than editing verdicts.

## 3. Accuracy calibration (live, labeled set)

Goal from PRD: ≥ 24/30 correct on a labeled set, zero confident-wrong `PASS` on contradicted claims.

- Labeled set: `examples/calibration.json` — 30 claims across `news-1.md`, `policy.md`, `pricing.md` (10 supported / 10 contradicted / 10 absent-or-opinion, each with an `expected` verdict and a note).
- Runner: `PYTHONPATH=src python3 tests/calibrate.py [--confidence T]` — batches live Jev calls, prints the confusion matrix, exits 0 only when the bar is met.
- Frozen matrix + notes: `examples/calibration.md` (threshold 0.7, `jev-1.13.0`, 30/30).
- Never move the threshold to hide a confident-wrong `PASS` — fix question wording instead (`instructions`/`criteria` in `verify.py`). Bump model version → re-run this layer.

## 4. Manual UX check (10 min)

- [ ] `sooth --help` alone explains enough to run.
- [ ] `sooth demo` works on a machine with no `TYPESAFE_API_KEY` and no network.
- [ ] Report readable by someone who never saw the tool (show one person).
- [ ] `--format json` output parses with `jq`-style tooling and `exit_code` matches `$?`.
- [ ] Missing key → one-line hint mentioning `TYPESAFE_API_KEY`, exit 3, no stack trace.
- [ ] Exit codes: all-PASS fixture → 0; with-REVIEW fixture → 2; with-FAIL → 1.
- [ ] Action runs in a scratch repo with `fail-on: fail|review|never` behaving as documented, and outputs readable in a later step.

## 5. Definition of done (v0.1)

1. `tests/test_core.py` green.
2. Smoke fixture behaves (§2) with a real key at least once.
3. Calibration table recorded (§3) and default threshold justified by it.
4. Manual checklist (§4) done.
5. Docs match reality: report column that shows probability distribution (not source snippets) — snippets deferred to v0.2 per `DESIGN.md`.

## Out of scope for testing now

Load/perf (CLI is one-shot), fuzzing, multi-language accuracy, regression CI on live API (costs money; add when thresholds ship to users).
