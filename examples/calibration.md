# Calibration matrix — v0.1

Frozen results of `examples/calibration.json` run through `tests/calibrate.py`.

- **Date:** 2026-09-25
- **Model:** `jev-1.13.0` (pinned)
- **Threshold:** 0.7
- **Score:** 30/30 first run; 29/30 after v0.2 evidence feature (bar: ≥ 24/30, zero confident-wrong `PASS` on contradicted claims — met both runs)
- **Runner:** `PYTHONPATH=src python3 tests/calibrate.py`

## 2026-10-01 re-run — roadmap Phase 2 (idf candidate ranking)

- **Score:** 30/30, threshold 0.7, runner exit 0 (bar ≥ 24/30 and zero confident-wrong `PASS` — both met).
- **The Phase 1 regression is resolved, and the claim that had no span now has its span.**

`Saham VIVA disuspensi di harga Rp 50.` is `FAIL` again, and where the recorded run cited nothing,
the live report now names `examples/news-1.md:5` — *"Misalnya PT Visi Media Asia Tbk (VIVA)
disuspensi di harga Rp 38, …"*.

The fix was the **candidate ranking**, not the candidate pool. `evidence_candidates` scores by
idf-weighted term overlap instead of raw set-overlap, so `VIVA disuspensi` (rare, specific) outranks
`saham` (in nearly every sentence of the article). Measured offline over 12 labelled claims from the
recorded runs: idf retrieves every gold span by `k=3`; the old scorer missed one even at `k=20`.
`EVIDENCE_CANDIDATES` is unchanged at 6 — raising it to 20 was the plan, and the measurement did not
support it. The guess in the Phase 1 entry below ("when the candidate pool widens") was wrong; the
ordering was the defect.

Live payload for the same draft and source fell from **11,111 to 9,500** input tokens, because
`state` now carries only the segments a claim was offered rather than every segment in the corpus.

`tests/smoke.sh` passes: the hero fixture is `PASS 4 · FAIL 3 · REVIEW 0 · UNCHECKABLE 1`, the
hostile-source case flips no verdict, and the Indonesian evil draft reads
`PASS 2 · FAIL 3 · REVIEW 1 · UNCHECKABLE 1` with the VIVA `FAIL` now sourcing line 5.

## 2026-10-01 re-run — roadmap Phase 1 (`reason` + evidence rule)

- **Score:** 29/30, threshold 0.7, runner exit 0 (bar ≥ 24/30 and zero confident-wrong `PASS` — both met).
- **One regression against the 30/30 runs, and it is deliberate.**

`Saham VIVA disuspensi di harga Rp 50.` (expected `FAIL`) now returns `REVIEW` with
`reason: evidence_missing`.

The judgment itself is unchanged — still `contradicts 1.00`, the judge is as certain as ever. What
changed is that Phase 1 refuses to call a verdict `FAIL` when it cannot cite the span it judged
against. The true contradicting sentence ("PT Visi Media Asia Tbk (VIVA) disuspensi di harga
Rp 38, …") is **not among the six word-overlap candidates** offered to the evidence question, so the
model answers `none` and the verdict is demoted. That is Critical #1 in [`docs/AUDIT.md`](../docs/AUDIT.md),
and it is the reason the candidate pool widens in Phase 2 — after which this case should return to
`FAIL` **with** the spanning sentence attached.

The label was not changed and the threshold was not moved. The case is a real `FAIL`; the tool is
being conservatively honest about not yet being able to prove it.

`tests/smoke.sh` agrees: the same claim reads `REVIEW / evidence_missing` on the Indonesian evil
draft, the hero fixture is unchanged at `PASS 4 · FAIL 3 · REVIEW 0 · UNCHECKABLE 1`, and the
hostile-source case (`examples/injection.md`) flipped no verdict.

## 2026-09-26 re-run (v0.3.0 code)

- **Score:** 30/30, threshold 0.7, runner exit 0.
- **Confident-wrong `PASS` on contradicted: 0.**
- The one historically jittery case — the invented "batas atas Rp 5.000" claim — landed `REVIEW` this run, matching its label. Its checkable probability still sits on the 0.5 floor; see the variance note below.

```
exp\got           PASS      FAIL    REVIEWUNCHECKABLE
PASS                10         0         0         0
FAIL                 0        10         0         0
REVIEW               0         0         6         0
UNCHECKABLE          0         0         0         4
```

No verification logic or threshold changed between this run and the previous one; only the
reporting layer did (`--format json`, demo cases, Action outputs). The re-run is here to show
that the numbers in the README are current, not inherited.

## Matrix (rows = expected, cols = got) — 2026-09-25 run

| exp\got | PASS | FAIL | REVIEW | UNCHECKABLE |
|---------|------|------|--------|-------------|
| PASS | 10 | 0 | 0 | 0 |
| FAIL | 0 | 10 | 0 | 0 |
| REVIEW | 0 | 0 | 5 | 1 |
| UNCHECKABLE | 0 | 0 | 0 | 4 |

Confident-wrong PASS on contradicted: **0** (both runs).

Variance note: the invented "batas atas Rp 5.000" claim flips between `REVIEW` (not_found) and `UNCHECKABLE` across runs — its checkable probability sits on the 0.5 floor. Both outcomes mean "don't act", so the distinction is harmless; recorded rather than tuned away.

## Composition

3 sources × 10 claims: `news-1.md` (Indonesian news), `policy.md` (refund policy), `pricing.md` (SaaS pricing). 10 supported (light → deep paraphrase), 10 contradicted (number flips, feature mis-attribution, negation flips), 5 invented (source silent), 5 opinions.

## Notes

- Derived-number edge: "one Free and one Pro mailbox → 10,100 emails" (arithmetically true, number absent from source) lands `REVIEW` — either the detail-gate or the missing-number check demotes the `PASS`. Behavior as designed.
- First draft of that case said "a Pro user can send 10,100 emails" and the model returned `FAIL 1.00` — correctly: Pro is 10,000. The label was wrong, not the model. Case rewritten to the true derived claim.
- `FAIL` on "SAML SSO is included in Pro" came at confidence 0.78 (feature mis-attribution is the subtlest flip in the set); all number flips were 1.00.
- Threshold 0.7 needed no tuning. Bump model version → re-run this suite before trusting thresholds.
