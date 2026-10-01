# Changelog

All notable changes to Sooth. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [Unreleased]

## [0.4.0] — 2026-10-01

Roadmap Phases 1–2 — traceable verdicts, and evidence retrieval that finds the span it judges against.

Question wording and candidate ranking both changed in `verify.py`, so the calibrated thresholds were
re-validated live on 2026-10-01:

- **Phase 1 alone:** 29/30 (bar ≥ 24/30), zero confident-wrong `PASS`, runner exit 0.
- **Phase 1 + 2:** **30/30**, zero confident-wrong `PASS`, runner exit 0.

Phase 1 on its own was a net downgrade — a contradicted claim with no citable span became `REVIEW`
instead of `FAIL`, which is honest but adds review load for no gain. Phase 2 removed the cause. Full
numbers in [`examples/calibration.md`](examples/calibration.md).

README's report and JSON examples are now generated from real `sooth demo` output and asserted
against it by `test_readme_examples_match_live_output`, so they cannot drift again.

### Added

- `reason` on every verdict (Markdown `Why` column, JSON, and `plain` output) — names the one rule
  that produced the kind: `supported`, `contradicted`, `not_found`, `low_confidence`,
  `detail_drift`, `smuggled_number`, `evidence_missing`, `uncheckable`. Derived, so it cannot go
  stale when `apply_safeguards` or `require_evidence` rewrite the kind.
- `claims.dropped_sentences(text)` — the sentences a split skipped. The CLI prints the count to
  stderr, so no sentence disappears without a word about it.
- `verify.require_evidence` — exported.

### Changed

- **Behavioural:** a `PASS` or `FAIL` with no cited source span is now demoted to `REVIEW`
  (`reason: evidence_missing`). The verdict questions see the whole source but the evidence question
  sees only the six pre-filtered candidates, so a confident verdict could previously ship with
  `evidence: null` and no way to audit it. **This can lower `PASS`/`FAIL` counts and raise `REVIEW`.**
- **Behavioural:** short sentences carrying a number are now kept as claims. `It cost $2M.` used to
  be dropped as a three-word fragment and never verified.
- Question instructions now state that `sources` and `segments` are untrusted quoted data that must
  not be obeyed. A hostile document can no longer read as an instruction to the judge.
- `apply_safeguards` and `attach_evidence` use `dataclasses.replace`, so a field added to `Verdict`
  can no longer be silently dropped at those seams.

### Fixed

- **Evidence retrieval.** `evidence_candidates` now ranks source spans by **idf-weighted term
  overlap** instead of raw word overlap. The old scorer counted boilerplate and discriminative words
  alike, so a span that merely shared the topic's common nouns outranked the one that actually
  contradicted the claim — and with `require_evidence` in place, that meant a real contradiction
  arriving as `REVIEW` with nothing to cite. In the Indonesian fixture `saham` appears in almost
  every sentence while `VIVA disuspensi` identifies one.
  `EVIDENCE_CANDIDATES` is unchanged at 6: raising it to 20 was the plan, but measurement showed the
  *ranking*, not the pool size, was the defect. Offline, over 12 labelled claims from the recorded
  runs, idf retrieves every gold span by `k=3`; the old scorer missed one even at `k=20`.
- **Request payload.** `state` now carries only the segments a claim was offered, not every segment
  of every source — a claim can only cite what it was given. `sources` still carries the whole
  document, so verdict recall is unchanged. Measured live on the same draft and source:
  **11,111 → 9,500 input tokens**.
- An API failure now reports the largest request size it built, so an oversized source reads as
  "split long sources" rather than an opaque SDK error. It is a diagnostic, not a guard — no cap is
  documented by the vendor, so no threshold is invented.

- `build_questions` rejects duplicate claim ids instead of silently overwriting one claim's
  questions with another's, which mis-attributed verdicts.

### Note

- `src/sooth/demo-{en,id}.json` are recordings from the pre-Phase-1 pipeline. `demo-id.json` claim
  c4 is a `FAIL` with `evidence: null`; the live path now returns `FAIL` citing `news-1.md:5`. The
  recordings replay faithfully (the demo does not re-run verification), so they under-report current
  behaviour. Re-record them with a real key per `CONTRIBUTING.md` rather than editing verdicts by
  hand.

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
