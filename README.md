# Sooth

**LLMs generate. Sooth verifies.**

Claim-by-claim hallucination detection for AI output. Sooth checks every sentence in a draft against your source material and returns `PASS` / `FAIL` / `REVIEW` — with calibrated probabilities, the exact source line behind each verdict, and exit codes that fail your build.

[![PyPI](https://img.shields.io/pypi/v/sooth.svg)](https://pypi.org/project/sooth/)
[![Python](https://img.shields.io/pypi/pyversions/sooth.svg)](https://pypi.org/project/sooth/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/naufalhilmiaji/sooth/blob/main/LICENSE)
[![CI](https://github.com/naufalhilmiaji/sooth/actions/workflows/ci.yml/badge.svg)](https://github.com/naufalhilmiaji/sooth/actions/workflows/ci.yml)

## Try it in 10 seconds — no API key

```bash
pip install sooth
sooth demo
```

`demo` replays a recorded run through the real reporting code. No network, no key, no signup.

## See it catch a hallucination

A model was asked to summarise a product release note. Three numbers came back wrong.

```
# Sooth

**PASS 4 · FAIL 3 · REVIEW 0 · UNCHECKABLE 1** — threshold 0.70

| # | Claim | Verdict | P | Why (P distribution) | Evidence |
|---|-------|---------|---|----------------------|----------|
| 1 | Kestrel Cloud launched API v3 on 14 August 2026 across all of its regions. | ✅ PASS | ████████ 1.00 | supports 1.00 / contradicts 0.00 / not_found 0.00 · details 0.86 | `examples/release-notes.md:7` "API v3 is generally available in all 12 regions, includin…" |
| 2 | The rate limit jumps to 2,000 requests per second per project, a twenty-fold increase over v2. | ❌ FAIL | ████████ 1.00 | supports 0.00 / contradicts 1.00 / not_found 0.00 · details 0.01 · missing #s: 2,000 | `examples/release-notes.md:11` "The rate limit rises from 100 requests per second to 500 …" |
| 3 | Token pricing falls to $0.002 per 1,000 input tokens, making it the cheapest mainstream inference API. | ❌ FAIL | ████████ 1.00 | supports 0.00 / contradicts 1.00 / not_found 0.00 · details 0.01 · missing #s: 0.002 | `examples/release-notes.md:15` "Token pricing drops to $0.004 per 1,000 input tokens and …" |
| 4 | Kestrel is now certified SOC 2 Type II, which unblocks enterprise procurement. | ❌ FAIL | ████████ 1.00 | supports 0.00 / contradicts 1.00 / not_found 0.00 · details 0.01 | `examples/release-notes.md:27` "SOC 2 Type II certification is still in progress and is n…" |
| 5 | The free tier now includes 10,000 requests per month. | ✅ PASS | ████████ 1.00 | supports 1.00 / contradicts 0.00 / not_found 0.00 · details 0.97 | `examples/release-notes.md:15` "The free tier now includes 10,000 requests per month, up …" |
| 6 | API v3 runs across 12 regions and held p99 latency of 180 ms through the beta. | ✅ PASS | ████████ 1.00 | supports 1.00 / contradicts 0.00 / not_found 0.00 · details 0.88 | `examples/release-notes.md:19` "Latency at p99 was 180 ms during the six-week beta." |
| 7 | Developers say the migration is the smoothest they have seen. | ➖ UNCHECKABLE | █░░░░░░░ 0.16 | P(checkable)=0.16 |  |
| 8 | Existing v2 keys keep working until 31 January 2027. | ✅ PASS | ████████ 1.00 | supports 1.00 / contradicts 0.00 / not_found 0.00 · details 0.99 | `examples/release-notes.md:7` "Existing v2 keys keep working until 31 January 2027." |

## Needs review

- line 3: Developers say the migration is the smoothest they have seen.
```

Exit code `1`. The build stops. No human had to notice that `2,000` should have been `500`, or that SOC 2 was still *in progress* in the source.

Every verdict carries its probability distribution and the source span it was judged against. When Sooth is unsure, it says `REVIEW` instead of guessing.

Reproduce that exact report offline with `sooth demo`. The inputs ship in [`examples/`](examples/): [`release-notes.md`](examples/release-notes.md) and [`ai-summary.md`](examples/ai-summary.md).

## Accuracy

Measured, not asserted. [`examples/calibration.json`](examples/calibration.json) is a hand-labelled set of 30 claims — 10 supported, 10 contradicted (number flips, feature mis-attribution, negation flips), 5 invented, 5 opinions — drawn from three documents (English policy, SaaS pricing, and Indonesian market news).

- **30/30 correct** verdicts, live, re-run 2026-09-26 on the v0.3.0 code. Bar is ≥ 24/30; the runner exits non-zero if it is missed.
- **Zero confident-wrong `PASS` on a contradicted claim, in every run.** This is the number that matters: a wrong `PASS` is the failure mode that ships garbage, so it is the one the runner gates on hardest.
- One case is inherently jittery: an invented claim whose checkable probability sits on the 0.5 floor, flipping between `REVIEW` and `UNCHECKABLE` across runs. Both outcomes mean "do not act on this". It is recorded rather than tuned away.

Full confusion matrix and notes: [`examples/calibration.md`](examples/calibration.md). Re-run it live with `PYTHONPATH=src python3 tests/calibrate.py`. The threshold has never been moved to hide a failure — when a case regressed, question wording in `verify.py` was fixed instead.

Honest caveat: 30 claims is a small set, labelled by the author, and it is not a substitute for evaluating Sooth on your own documents. It is a regression gate, not a benchmark claim.

## Install

```bash
pip install sooth
export TYPESAFE_API_KEY=...       # get one at console.typesafe.ai
```

Requires Python 3.11+. Judgments come from [Jev](https://docs.typesafe.ai) (TypeSafe System One), which returns typed distributions instead of generated prose.

## Usage

```bash
sooth --source docs/policy.md --source tickets/t123.md --text draft-reply.md

# CI-friendly exit codes
sooth --source policy.md --text draft.md --format plain
#   0 = clean  ·  1 = any FAIL  ·  2 = any REVIEW  ·  3 = usage/config error

# Options
#   --confidence T   REVIEW below this confidence (default 0.7)
#   --format md|plain|json
#   -o FILE          write report to file
#   --log FILE       append full judgment trace (one JSONL line per run)
#   --version
```

## Machine-readable output

`--format json` gives pipelines and agents a stable contract — no prose parsing, and the exit code is stated in the payload:

```json
{
  "summary": { "pass": 4, "fail": 3, "review": 0, "uncheckable": 1, "threshold": 0.7 },
  "exit_code": 1,
  "verdicts": [
    {
      "id": "c2",
      "text": "The rate limit jumps to 2,000 requests per second per project…",
      "line": 3,
      "kind": "FAIL",
      "choice": "contradicts",
      "probabilities": { "supports": 0.0, "contradicts": 1.0, "not_found": 0.0 },
      "confidence": 1.0,
      "details_p": 0.01,
      "missing_numbers": ["2,000"],
      "evidence": {
        "text": "The rate limit rises from 100 requests per second to 500 requests per second per project.",
        "line": 11,
        "source": "examples/release-notes.md"
      }
    }
  ]
}
```

## Use it as a CI quality gate

```yaml
- name: Verify AI output
  uses: naufalhilmiaji/sooth@v0.3.0
  with:
    source: docs/policy.md
    text: generated-reply.md
    fail-on: review        # review (default) | fail | never
  env:
    TYPESAFE_API_KEY: ${{ secrets.TYPESAFE_API_KEY }}
```

The step fails the build on `FAIL` — and on `REVIEW`, so nothing uncertain ships silently. Set `fail-on: fail` to block only on hard contradictions. The full report is appended to the job summary.

Consume the counts in later steps:

```yaml
- id: sooth
  uses: naufalhilmiaji/sooth@v0.3.0
  with: { source: policy.md, text: draft.md, fail-on: never }
  env: { TYPESAFE_API_KEY: "${{ secrets.TYPESAFE_API_KEY }}" }

- run: echo "${{ steps.sooth.outputs.verdicts }}"   # PASS 1, FAIL 1, REVIEW 0, UNCHECKABLE 0
```

Outputs: `verdicts`, `pass-count`, `fail-count`, `review-count`, `uncheckable-count`, `report`, `exit-code`.

Prefer plain shell? `sooth --source policy.md --text draft.md` gives the same exit codes.

## How it works

1. Draft is split into claims (one sentence each).
2. Each claim gets four questions to Jev, fanned out in parallel batches: *is this checkable?*, *does the source support it?* (`supports` / `contradicts` / `not_found`), *do all details match exactly?*, and *which source span is the evidence?*
3. Verdicts are mapped in code: uncheckable → `UNCHECKABLE`; low confidence → `REVIEW`; then `PASS` / `FAIL`. Safeguards demote `PASS` to `REVIEW` when details drift or claim numbers are absent from the source (checked in plain code).
4. The report shows the full probability distribution per claim — not just a label.

The decision logic lives in [`src/sooth/verify.py`](https://github.com/naufalhilmiaji/sooth/blob/main/src/sooth/verify.py) in a dozen readable lines. Change thresholds and rules there, not in prompts.

## Why not just use an LLM judge?

Not claiming Sooth is universally more accurate. Claiming it gives you **architectural guarantees** a prompt cannot:

| | Sooth | Generic LLM judge |
|---|-------|-------------------|
| Claim-level verification | ✅ | Sometimes |
| Source span behind each verdict | ✅ | Sometimes |
| `PASS` / `FAIL` / `REVIEW` | ✅ fixed vocabulary | Generated labels |
| Probability distribution | ✅ | Usually none |
| Verdict rules in readable code | ✅ | Prompt-dependent |
| CI exit codes | ✅ | ❌ |
| Audit log (`--log` JSONL) | ✅ | DIY |
| Runs the same verdict twice | ✅ deterministic mapping | Sampling variance |

An LLM judge gives you a sentence about your text. Sooth gives you a decision your code can branch on, and the evidence it branched on.

## Who it's for

Developers building systems that generate text from trusted material:

- **RAG pipelines** — retrieved the right document, still wrote the wrong number
- **AI agents** — before an agent's reply reaches a human
- **Support / ops copilots** — policy-backed answers, checked against the policy
- **Report & summary generation** — figures that must match the source
- **Compliance workflows** — evidence trail for every claim, not vibes

## Beyond English

The bundled Indonesian case proves the pipeline is not English-only: `sooth demo --case id` replays a recorded run against Indonesian market news, where three fabricated figures are caught. Non-English claim segmentation needs a whitespace-language sentence splitter (Indonesian, Malay, and most European languages are fine; Chinese and Japanese would need a different splitter — see [`src/sooth/claims.py`](https://github.com/naufalhilmiaji/sooth/blob/main/src/sooth/claims.py)).

## Known limits (alpha)

- Safeguards catch most drift and smuggling: claim numbers absent from the source demote `PASS` to `REVIEW`, and a detail-match gate flags altered hedges ("about 74%" → "over 74%"). Not perfect — read the `Why` column before trusting a verdict.
- Derived numbers (totals, values computed outside the source) look "missing" and land in `REVIEW`.
- Source + questions must fit ~64k tokens — split long documents yourself.
- Sentence splitting is regex-based: abbreviations and quoted sentences can mis-split.
- Requires a TypeSafe API key for anything beyond `sooth demo`.

## Development

```bash
git clone https://github.com/naufalhilmiaji/sooth && cd sooth
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

python3 tests/test_core.py     # pure checks, no network, under a second
pytest                         # same suite
bash tests/test_action.sh      # GitHub Action arg wiring + fail-on policy
ruff check src tests           # lint (CI gate)

export TYPESAFE_API_KEY=...    # only for the two live layers below
bash tests/smoke.sh                          # live end-to-end, both fixtures
PYTHONPATH=src python3 tests/calibrate.py    # live calibration, 30 labeled claims
```

Docs: [PRD](https://github.com/naufalhilmiaji/sooth/blob/main/docs/PRD.md) · [Design](https://github.com/naufalhilmiaji/sooth/blob/main/docs/DESIGN.md) · [Testing](https://github.com/naufalhilmiaji/sooth/blob/main/docs/TESTING.md) · [Changelog](https://github.com/naufalhilmiaji/sooth/blob/main/CHANGELOG.md)

## Roadmap

- **v0.3.0** — `--format json`, `sooth demo --case`, Action `fail-on` + outputs
- **v0.2.3** shipped — GitHub Action: CI quality gate in one `uses:` line
- **v0.2.2** shipped — `sooth demo` (offline, no API key)
- **v0.2.1** shipped — source-span evidence, published on PyPI
- later — pluggable backends (local models), hosted web app, review queues

## License

MIT © Naufal Hilmiaji. Powered by [TypeSafe](https://typesafe.ai) / Jev.
