# PRD — Sooth (v0.1)

## Problem

AI writes text fast. Nobody checks it. Wrong claims ship. In 2026 most drafts (support replies, docs, reports, PR descriptions) are AI-written and reviewed by skimming humans.

Sooth is a cheap, automatic checker: does each claim in the AI draft actually follow from the source material?

It targets the AI-era verification gap: AI writes fast, nobody checks before shipping. Opaque AI decisions are addressed by design: every verdict shows its probability distribution, and `--log` records the full judgment trace.

## What it is

CLI tool. Input: source text(s) + AI-generated draft. Output: a **trust report** — every claim marked `PASS` / `FAIL` / `REVIEW`, with probability, reason, and source snippet.

Engine by [Jev](https://docs.typesafe.ai) (TypeSafe System One): typed judgments + calibrated probabilities, not generated prose.

## Who it is for (v0.1)

Developers and technical teams who already work in a terminal and pipe AI output into things: CI jobs, agent pipelines, release notes, support macros.

## User story

```
sooth --source docs/policy.md --source tickets/t123.md --text draft-reply.md
```

1. User gives sources (ground truth) and draft (AI text to verify).
2. Tool splits draft into claims (sentence per claim in v0.1).
3. Each claim judged against sources: supported / contradicted / not found — plus "is this even checkable?".
4. Report printed as markdown. Low-confidence claims land in `REVIEW` instead of fake-precise verdicts.
5. Optional `--log decisions.jsonl` appends full judgment trace (audit trail seed).

## Report shape (contract)

| # | Claim | Verdict | P | Why (v0.1) |
|---|-------|---------|---|------------|
| 1 | Refunds are processed in 3 days. | ✅ PASS | 0.91 | supports .91 / contradicts .02 / not_found .07 |
| 2 | We support Bitcoin. | ❌ FAIL | 0.87 | supports .03 / contradicts .87 / not_found .10 |
| 3 | Customers love the change. | ⚠️ REVIEW | 0.54 | not found in sources |

v0.1 "Why" = probability distribution. Source-snippet evidence = v0.2 (see `DESIGN.md`).

Verdict rules (fixed, readable in code):

- claim not checkable (opinion, vague) → `UNCHECKABLE` (listed under REVIEW section)
- `supports` + confidence ≥ threshold → `PASS`
- `contradicts` + confidence ≥ threshold → `FAIL`
- `not in source` **or** confidence < threshold → `REVIEW`

Default threshold 0.7, flag `--confidence`.

## MVP scope

In:

- CLI: `sooth --source … [--source …] --text … [--confidence T] [--log FILE] [--format md|plain]`
- Plain text / markdown input (UTF-8). Multiple sources.
- Sentence-per-claim splitting.
- Jev fan-out verification (batched).
- Markdown report to stdout (or `-o FILE`).
- JSONL decision log (`--log`).
- Exit codes for CI: `0` all PASS/CLEAN, `1` any FAIL, `2` any REVIEW remaining, `3` usage/config error.

Out (v0.1 — later or never):

- Web UI (paid phase), PDF/HTML parsing, images
- Smarter claim splitting (clauses, bullet merging)
- Team features, history, webhooks
- Non-English tuning (Jev is English-strongest)
- Custom question editing UI

## Success criteria (v0.1 done when)

1. `sooth` runs end-to-end against a sample fixture and prints the report above.
2. On a hand-labeled set of 30 claims (10 supported / 10 contradicted / 10 absent-or-fluff): ≥ 24 correct verdicts after threshold tuning, no confident (≥0.7) wrong `PASS` on a contradicted claim in the set.
3. CI-usable: exit codes behave; works without network when `--log`-replaying a fixture later (replay is stretch).
4. One new user understands the output with no explanation beyond `--help`.

## Monetization (later — not built now)

Free OSS: CLI + library. Paid web app later: paste UI, history, team folders, "verify before publish" API. Same engine. No paywall logic in v0.1.

## Open decisions (defaults chosen, reversible)

| Decision | Default | Note |
|----------|---------|------|
| Language | Python 3.11+ | official Jev Python SDK |
| Claim split | sentence regex | upgrade when it mis-splits real drafts |
| Batch size | 30 claims/request | stay well under 64k token cap |
| REVIEW exit code | 2 | CI can choose to ignore |
