# Sooth

**LLMs generate. Sooth verifies.**

Claim-by-claim fact-checking for AI output, designed for CI. Sooth checks every sentence in a draft against your source material and returns `PASS` / `FAIL` / `REVIEW` with calibrated probabilities and the exact source line behind each verdict.

[![PyPI](https://img.shields.io/pypi/v/sooth.svg)](https://pypi.org/project/sooth/)
[![Python](https://img.shields.io/pypi/pyversions/sooth.svg)](https://pypi.org/project/sooth/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/naufalhilmiaji/sooth/blob/main/LICENSE)
[![CI](https://github.com/naufalhilmiaji/sooth/actions/workflows/ci.yml/badge.svg)](https://github.com/naufalhilmiaji/sooth/actions/workflows/ci.yml)

## See it catch a hallucination

```bash
pip install sooth
sooth demo        # no API key needed
```

Real output — seven claims in an AI-written news summary, three numbers quietly wrong:

```
# Sooth

**PASS 2 · FAIL 3 · REVIEW 1 · UNCHECKABLE 1** — threshold 0.70

| # | Claim | Verdict | P | Why (P distribution) | Evidence |
|---|-------|---------|---|----------------------|----------|
| 3 | BNBR baru menuntaskan rights issue bernilai besar di harga Rp 33. | ❌ FAIL | ████████ 1.00 | contradicts 1.00 / not_found 0.00 / supports 0.00 · details 0.01 · missing #s: 33 | `examples/news-1.md:25` "Saham ini juga baru menyelesaikan rights issue dalam juml…" |
| 5 | BUMI hanya perlu turun sekitar 10% untuk menyentuh level Rp 50. | ❌ FAIL | ████████ 1.00 | contradicts 1.00 / not_found 0.00 / supports 0.00 · details 0.01 · missing #s: 10 | `examples/news-1.md:23` "Adapun PT Bumi Resources Tbk (BUMI) di sekitar Rp192 haru…" |
| 6 | BEI juga menetapkan batas atas harga saham Rp 5.000 per saham. | ⚠️ REVIEW | ████████ 1.00 | contradicts 0.00 / not_found 1.00 / supports 0.00 · details 0.02 · missing #s: 5.000 |  |
| 7 | Para investor ritel sangat senang dengan aturan baru ini. | ➖ UNCHECKABLE | ██░░░░░░ 0.24 | P(checkable)=0.24 |  |
```

Every verdict carries its probability distribution and the source span it was judged against. When Sooth is unsure, it says `REVIEW` instead of guessing.

## Why

AI writes fast, nobody checks. Claims ship wrong — usually a number, a hedge, or a name that drifted. Asking another LLM "is this right?" just produces more prose.

Sooth takes a different bet: **the model makes typed judgments, code makes the decision.** Every rule that turns a probability into a verdict is a readable line of Python, not a prompt.

## Install

```bash
pip install sooth
export TYPESAFE_API_KEY=...       # get one at console.typesafe.ai
```

## Usage

```bash
sooth --source docs/policy.md --source tickets/t123.md --text draft-reply.md

# CI-friendly exit codes
sooth --source policy.md --text draft.md --format plain
#   0 = clean  ·  1 = any FAIL  ·  2 = any REVIEW  ·  3 = usage/config error

# Options
#   --confidence T   REVIEW below this confidence (default 0.7)
#   --format md|plain
#   -o FILE          write report to file
#   --log FILE       append full judgment trace (one JSONL line per run)
```

Wire it into CI as a quality gate for generated content:

```yaml
- name: Verify AI output
  run: sooth --source docs/policy.md --text generated-reply.md
  env:
    TYPESAFE_API_KEY: ${{ secrets.TYPESAFE_API_KEY }}
```

## How it works

1. Draft is split into claims (one sentence each).
2. Each claim gets four questions to Jev, fanned out in parallel batches: *is this checkable?*, *does the source support it?* (`supports` / `contradicts` / `not_found`), *do all details match exactly?*, and *which source span is the evidence?*
3. Verdicts are mapped in code: uncheckable → `UNCHECKABLE`; low confidence → `REVIEW`; then `PASS` / `FAIL`. Safeguards demote `PASS` to `REVIEW` when details drift or claim numbers are absent from the source (checked in plain code).
4. The report shows the full probability distribution per claim — not just a label.

The decision logic lives in [`src/sooth/verify.py`](https://github.com/naufalhilmiaji/sooth/blob/main/src/sooth/verify.py) in a dozen readable lines. Change thresholds and rules there, not in prompts.

Judgments come from [Jev](https://docs.typesafe.ai) (TypeSafe System One), which returns typed distributions instead of generated prose.

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

## Who it's for

Developers building systems that generate text from trusted material:

- **RAG pipelines** — retrieved the right document, still wrote the wrong number
- **AI agents** — before an agent's reply reaches a human
- **Support / ops copilots** — policy-backed answers, checked against the policy
- **Report & summary generation** — figures that must match the source
- **Compliance workflows** — evidence trail for every claim, not vibes

## Known limits (alpha)

- Safeguards catch most drift and smuggling: claim numbers absent from the source demote `PASS` to `REVIEW`, and a detail-match gate flags altered hedges ("about 74%" → "over 74%"). Not perfect — read the `Why` column before trusting a verdict.
- Derived numbers (totals, values computed outside the source) look "missing" and land in `REVIEW`.
- Source + questions must fit ~64k tokens — split long documents yourself.

## Development

```bash
pip install -e ".[dev]"
python3 tests/test_core.py     # pure checks, no network
pytest                         # same suite
bash tests/smoke.sh            # live smoke (needs TYPESAFE_API_KEY)
PYTHONPATH=src python3 tests/calibrate.py   # live calibration, 30 labeled claims
```

Docs: [PRD](https://github.com/naufalhilmiaji/sooth/blob/main/docs/PRD.md) · [Design](https://github.com/naufalhilmiaji/sooth/blob/main/docs/DESIGN.md) · [Testing](https://github.com/naufalhilmiaji/sooth/blob/main/docs/TESTING.md)

## Roadmap

- v0.2.2 shipped: `sooth demo` (offline, no API key)
- v0.2.1 shipped: source-span evidence, published on PyPI
- GitHub Action
- later: hosted web app — paste UI, history, team review queues

## License

MIT © Naufal Hilmiaji. Powered by [TypeSafe](https://typesafe.ai) / Jev.
