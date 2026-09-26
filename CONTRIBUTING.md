# Contributing to Sooth

Thanks for looking. This is a small tool with a narrow contract, and the fastest way to get a change merged is to keep it narrow.

## Set up

```bash
git clone https://github.com/naufalhilmiaji/sooth
cd sooth
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

## Run the checks

```bash
python3 tests/test_core.py     # pure checks — no network, no API key, under a second
pytest                         # same suite through pytest
bash tests/test_action.sh      # GitHub Action arg wiring, outputs, and fail-on policy
ruff check src tests           # lint — CI runs this, line length 100
```

Two optional layers need a live key (`TYPESAFE_API_KEY` from [console.typesafe.ai](https://console.typesafe.ai)):

```bash
bash tests/smoke.sh                          # end-to-end against the live API
PYTHONPATH=src python3 tests/calibrate.py    # 30-claim calibration; exits non-zero if the bar is missed
```

CI never calls the live API — it would cost money and add flakiness on forks. Run the live layers yourself before a release.

## Ground rules

**Never move the threshold to hide a failure.** If calibration regresses, the fix is question wording in `build_questions()` in `src/sooth/verify.py`, not a lower `--confidence` default and not a relaxed labelled case. The calibration matrix is frozen in `examples/calibration.md`; if you change it, say why in the diff.

**No new runtime dependencies** without a discussion issue first. The runtime dependency list is exactly one package (`typesafe-sdk`); a verifier that drags in a dependency tree is a verifier nobody installs into a CI job.

**Verdict mapping stays pure and readable.** `map_verdict` and `apply_safeguards` take values and return values. Network I/O lives in `verify_claims` only. If your change makes the decision path untestable without a key, it will not be merged.

**Deterministic checks belong in code, not in prompts.** If a rule can be expressed as a regex or an arithmetic comparison — like the number-smuggling check in `missing_numbers()` — it belongs in Python, where it can be tested and audited.

**Fixed vocabulary.** Verdicts are `PASS`, `FAIL`, `REVIEW`, `UNCHECKABLE` and nothing else. Resist adding states.

## Adding a demo case

`sooth demo` must keep working with no API key and no network. To add one:

1. Add the source and draft documents under `examples/`.
2. Run a real verification with `--log` and keep the output:
   ```bash
   sooth --source examples/your-source.md --text examples/your-draft.md --log /tmp/run.jsonl
   ```
3. Save that single JSONL line as `src/sooth/demo-<case>.json`.
4. Register it in `DEMO_CASES` in `src/sooth/cli.py`.
5. `pytest` covers the rest — `test_demo_fixtures_are_valid_records` and `test_cli_demo_replays_offline` will fail if the record or the wiring is wrong.

Demo records are real recorded runs. Do not hand-edit verdicts to make a demo look better; re-run and commit what the model actually returned.

## Adding calibration claims

Append to `examples/calibration.json` with an `expected` verdict and a one-line note explaining why that label is correct. Then re-run `tests/calibrate.py` live and update `examples/calibration.md` with the new matrix. Cases that reveal a wrong answer are more valuable than cases that confirm the tool works — record those, and explain the failure mode.

## Reporting a wrong verdict

The most useful bug report includes: the source document, the draft, the verdict Sooth returned, the verdict you expected, and the `--format json` payload for that claim. Include the `Why` column — the probability distribution usually makes the cause obvious.

## Pull requests

- One thing per PR. A feature and a refactor in the same diff will be asked to split.
- Add or update a test in `tests/test_core.py` for any change to logic in `claims.py`, `verify.py`, or `report.py`.
- Update `CHANGELOG.md` under `## [Unreleased]`.
- Commit messages: `feat:`, `fix:`, `docs:`, `chore:`, `test:` — the repo log is readable, keep it that way.
