# Changelog

All notable changes to Sooth. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

## [0.3.0] — 2026-09-26

Presentation and machine-consumption release. No change to verification behaviour or to any calibrated threshold.

### Added

- `--format json` — stable machine-readable report (`summary`, `exit_code`, `verdicts[]` with probabilities, evidence, and missing numbers). One JSON contract for pipelines and agents instead of scraping Markdown.
- `sooth demo --case en|id` — two bundled recorded runs now ship in the wheel. `en` is the default (release notes vs an AI summary, three numbers silently wrong); `id` is the Indonesian market-news case.
- `--version`, reading the version from installed distribution metadata.
- GitHub Action: `fail-on` input (`review` default, `fail`, `never`), and `outputs` — `verdicts`, `pass-count`, `fail-count`, `review-count`, `uncheckable-count`, `report`, `exit-code`. All from a single API call.
- English calibration fixture (`examples/release-notes.md` + `examples/ai-summary.md`) as the default demo.
- CI: an offline demo smoke step that pins the documented exit codes and the JSON contract, plus a `package` job that installs the built wheel and replays both demo cases (guards non-Python package data).
- `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`.

### Changed

- README rewritten around the measured accuracy numbers and an English hero demo.
- Action installs the exact version declared in its own `pyproject.toml`, so the pin can no longer drift from the tag.
- PyPI metadata: keywords and classifiers now cover `hallucination`, `fact-checking`, `llm-evaluation`, `rag`, `guardrails`, `ci`, `github-action`.
- `render_json` and the `--log` record now share one verdict-serialisation function, so the two JSON surfaces cannot drift apart.

### Fixed

- `sooth.__version__` reported `0.1.0` while the distribution was `0.2.3`. Now sourced from packaging metadata; a test fails if it ever becomes a hardcoded literal again.
- `tests/smoke.sh` invoked the bare `python3`, which fails when `typesafe-sdk` only exists in the project venv. It now prefers an active venv, then `./.venv`, then `python3`, accepts `PYTHON=`, and explains the fix instead of exiting 3 silently.

## [0.2.3] — 2026-09-25

### Added

- GitHub Action — a CI quality gate in one `uses:` line, with the report appended to the job summary.

## [0.2.2] — 2026-09-25

### Added

- `sooth demo` — replays a bundled recorded run offline, no API key needed.
- README overhaul with a recorded demo.

## [0.2.1] — 2026-09-25

### Added

- Source-span evidence behind every verdict: sources are split into sentence segments, code pre-ranks ~6 candidates per claim, and a per-claim Choice selects the best span.
- First PyPI release.

## [0.2.0] — 2026-09-25

### Added

- Source-span evidence behind every verdict (`v0.2` feature branch).
- 30-claim calibration set with a live runner and a frozen confusion matrix.

### Fixed

- Ruff lint violations blocking CI.

## [0.1.0-alpha] — 2026-09-24

### Added

- Initial CLI: `sooth --source … --text …`, sentence-per-claim splitting, Jev fan-out verification (four questions per claim in one batched call), Markdown report, `--log` JSONL decision ledger, CI exit codes, `--confidence` threshold.
- Safeguards: detail-match gate and deterministic number-smuggling check demote `PASS` to `REVIEW`.
- PRD, technical design, and testing docs.
