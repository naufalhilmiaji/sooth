# Calibration matrix — v0.1

Frozen results of `examples/calibration.json` run through `tests/calibrate.py`.

- **Date:** 2026-09-25
- **Model:** `jev-1.13.0` (pinned)
- **Threshold:** 0.7
- **Score:** 30/30 first run; 29/30 after v0.2 evidence feature (bar: ≥ 24/30, zero confident-wrong `PASS` on contradicted claims — met both runs)
- **Runner:** `PYTHONPATH=src python3 tests/calibrate.py`

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
