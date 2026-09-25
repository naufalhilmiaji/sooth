# Technical Design — Sooth v0.1

Companion to `PRD.md`. Stack and data flow only. No speculative layers.

## Stack

- Python 3.11+, official `typesafe-sdk` package (`TypeSafeClient.system_one`), stdlib otherwise (argparse, re, json, pathlib).
- No web framework, no DB, no plugin system. Four modules + CLI entry is enough.

## Layout (src layout, standard packaging)

```
src/sooth/
  __init__.py   # package API
  claims.py     # split text → claims (pure)
  verify.py     # build Jev questions, call API, map answers → verdicts (pure map + one I/O call)
  report.py     # verdicts → markdown / plain text + JSONL log record (pure)
  cli.py        # argparse, file I/O, exit codes, --log writer
tests/
  conftest.py
  test_core.py  # asserts for pure functions + verdict mapping
  smoke.sh      # optional live smoke (real key)
examples/       # fixture: source.md, draft.md
docs/           # PRD, DESIGN, TESTING
```

## Flow

```
sources + draft
   → claims.split(draft)            → list[Claim]
   → verify.batch(claims, sources)  → list[Verdict]     # 1..n Jev calls
   → report.render(verdicts)        → markdown string
   → stdout / -o file
   → optional JSONL log append
```

Pure functions everywhere except `verify.call_jev()` and file I/O. Testable without network.

## Claim splitting (`claims.py`)

v0.1: sentence splitter on `.`/`!`/`?` + newline, keeping numbers intact (`3.5 days`). Drop empties and pure questions? No — questions are claims too ("Does it support X?" is checkable as written intent… actually drop interrogatives and headings, they are not claims). Rules:

- Keep: declarative sentences, ≥ 4 words.
- Skip: headings (`# …`), list bullets' leading markers kept as text, sentences < 4 words, lines that end with `?`.
- Each claim keeps `text` + `source_span` = `{file, line}` of origin (for "claim #3 came from draft line 12").

```python
# ponytail: regex splitter, mis-splits quotes/abbreviations; upgrade to clause-level when real drafts demand
```

## Jev request (`verify.py`)

One request per batch of ≤ 30 claims. State is shared; questions reference claims by path.

```jsonc
// state
{
  "sources": [
    { "name": "policy.md", "text": "…" },          // concatenated if many; name kept for evidence line
    { "name": "tickets/t123.md", "text": "…" }
  ],
  "claims": [
    { "id": "c1", "text": "Refunds are processed in 3 days." },
    { "id": "c2", "text": "We support Bitcoin." }
  ]
}
```

Per claim, **three parallel questions** (fan-out pattern; statement text is embedded in the instructions):

```jsonc
"c1_checkable": {
  "type": "noul",
  "instructions": "Statement: <claim text>\n\nIs the statement a concrete factual claim that the evidence in `sources` could support or contradict? ...",
  // noul answer = P(checkable)
},
"c1_verdict": {
  "type": "choice",
  "instructions": "Statement: <claim text>\n\nDoes the evidence in `sources` support the statement?",
  "criteria": {
    "supports":    "...",
    "contradicts": "...",
    "not_found":   "..."
  }
  // choice + probabilities + confidence
},
"c1_details": {
  "type": "noul",
  "instructions": "Statement: <claim text>\n\nDoes EVERY specific detail — names, numbers, dates, comparisons such as 'more than' or 'about' — exactly match the evidence in `sources`? ...",
  // noul answer = P(all details match)
}
```

- 30 claims → 90 questions, one call. Over batch cap or 422 → split and retry half (SDK retries 429/529 already).
- Pin model `jev-1.13.0` (thresholds tuned against it). Constant in `verify.py`.
- API key: env `TYPESAFE_API_KEY`. Missing → exit 3 with one-line hint.

## Verdict mapping (pure)

```
if p_checkable < 0.5:              → UNCHECKABLE
elif confidence < threshold:       → REVIEW
elif choice == "supports":         → PASS
elif choice == "contradicts":      → FAIL
else:                              → REVIEW          # not_found
```

Then safeguards (`apply_safeguards`, pure) — demote `PASS` → `REVIEW` when:

- `details_p < 0.5` (detail-gate Noul says some detail drifted), or
- `missing_numbers(claim, sources)` non-empty — claim numbers absent from every source (regex extraction, separator-normalized; no model involved).

FAIL/REVIEW/UNCHECKABLE pass through untouched.

`Verdict = {claim_id, claim_text, draft_line, kind, p_checkable?, choice?, probabilities, confidence, details_p?, missing_numbers}`

Evidence snippet v0.1: none auto-extracted — show top-1 "why" as the choice's probability distribution (`supports 0.91 / contradicts 0.02 / not_found 0.07`). Real source-span extraction = v0.2 (span-selection cookbook). Report column renders this distribution; label it "P(supports/contradicts/not_found)".

```python
# ponytail: evidence is a distribution, not a source quote; add span extraction when users ask "where?"
```

(If PRD table showed source snippets — that is v0.2. v0.1 report substitutes distribution; PRD example is target UX.)

## Report (`report.py`)

Markdown: summary line (`PASS n · FAIL n · REVIEW n · UNCHECKABLE n`), then one table as in PRD, ASCII probability bar in P column (`██████░░ 0.91` is enough; no unicode-only requirement). FAIL rows first? No — keep draft order, print summary counts first. `REVIEW` and `UNCHECKABLE` share a section below the table if any.

## Decision log (`--log`)

Append-only JSONL, one object per run (not per claim — one line, pretty fields):

```json
{"ts": "…", "model": "jev-1.13.0", "threshold": 0.7, "sources": ["policy.md"], "draft": "draft-reply.md", "usage": {"input_tokens": 0, "output_tokens": 0}, "results": [ …verdicts with full probabilities… ]}
```

This is the decision-ledger seed (audit trail). No viewer in v0.1.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | all PASS or UNCHECKABLE only |
| 1 | any FAIL |
| 2 | any REVIEW (no FAIL) |
| 3 | usage / missing key / unreadable file |

## Errors

- SDK raises typed errors; catch at CLI boundary, print one line to stderr, exit 3 (or 2 on API failure mid-run? → exit 3, "could not verify", never print a partial report marked complete).
- Empty draft → usage error. Empty sources → usage error (nothing to check against).

## Security

- Key via env only, never logged, never in `--log`.
- Files read as UTF-8 text. No shell-out, no eval. `--log` path user-controlled write (documented).
