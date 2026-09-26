## What

## Why

## Checklist

- [ ] `python3 tests/test_core.py` passes
- [ ] `bash tests/test_action.sh` passes (if `action.yml` / `action.sh` changed)
- [ ] `ruff check src tests` is clean
- [ ] New logic covered by an assert in `tests/test_core.py`
- [ ] Docs updated if behavior changed (`docs/PRD.md`, `docs/DESIGN.md`, `docs/TESTING.md`, README)
- [ ] `CHANGELOG.md` updated under `## [Unreleased]`

## For verdict or accuracy changes

- [ ] No calibrated threshold was lowered to make a case pass
- [ ] Relevant demo records re-recorded from a live run rather than hand-edited
