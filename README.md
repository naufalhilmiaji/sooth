# Sooth

Verify AI-generated text against source material. Claim-by-claim **PASS / FAIL / REVIEW**, with calibrated probabilities you can act on in CI.

Built on [Jev](https://docs.typesafe.ai) (TypeSafe System One) — typed judgments and probabilities instead of generated prose. Every verdict shows its probability distribution, and the combination rules are plain code you can read. No black box.

```
sooth --source policy.md --text draft-reply.md
```

```
# Sooth

PASS 1 · FAIL 1 · REVIEW 1 · UNCHECKABLE 0** — threshold 0.70

| #   | Claim                                                | Verdict  | P             | Why (P distribution)                              |
| --- | ---------------------------------------------------- | -------- | ------------- | ------------------------------------------------- |
| 1   | Refunds are processed within three days of approval. | ✅ PASS   | ████████ 0.91 | supports 0.91 / contradicts 0.02 / not_found 0.07 |
| 2   | We also support Bitcoin payments.                    | ❌ FAIL   | ███████░ 0.87 | supports 0.03 / contradicts 0.87 / not_found 0.10 |
| 3   | Customers love the change.                           | ⚠️ REVIEW | ████░░░░ 0.54 | supports 0.20 / contradicts 0.05 / not_found 0.75 |

## Needs review

- line 5: Customers love the change.
```

## Why

AI writes fast, nobody checks. Claims ship wrong. Sooth checks each claim against the evidence you give it — and when it is unsure, it says `REVIEW` instead of guessing.

## Install

```bash
pip install sooth          # or: pip install -e ".[dev]" from source
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

## How it works

1. Draft is split into claims (one sentence each).
2. Each claim gets three questions to Jev, all fanned out in parallel batches: *is this checkable?*, *does the source support it?* (`supports` / `contradicts` / `not_found`), and *do all details match exactly?*
3. Verdicts are mapped in code: uncheckable → `UNCHECKABLE`; low confidence → `REVIEW`; then `PASS` / `FAIL`. Safeguards demote `PASS` to `REVIEW` when details drift or claim numbers are absent from the source (checked in plain code).
4. The report shows the full probability distribution per claim — not just a label.

The decision logic lives in [`src/sooth/verify.py`](src/sooth/verify.py) in a dozen readable lines. Change thresholds and rules there, not in prompts.

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

Docs: [PRD](docs/PRD.md) · [Design](docs/DESIGN.md) · [Testing](docs/TESTING.md)

## Roadmap

- v0.2: source-span evidence (the exact sentence that backs each claim)
- later: hosted web app — paste UI, history, team review queues

## License

MIT © Naufal Hilmiaji. Powered by [TypeSafe](https://typesafe.ai) / Jev.
