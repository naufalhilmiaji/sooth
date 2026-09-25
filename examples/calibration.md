# Calibration matrix — v0.1

Frozen results of `examples/calibration.json` run through `tests/calibrate.py`.

- **Date:** 2026-09-25
- **Model:** `jev-1.13.0` (pinned)
- **Threshold:** 0.7
- **Score:** 30/30 (bar: ≥ 24/30, zero confident-wrong `PASS` on contradicted claims)
- **Runner:** `PYTHONPATH=src python3 tests/calibrate.py`

## Matrix (rows = expected, cols = got)

| exp\got | PASS | FAIL | REVIEW | UNCHECKABLE |
|---------|------|------|--------|-------------|
| PASS | 10 | 0 | 0 | 0 |
| FAIL | 0 | 10 | 0 | 0 |
| REVIEW | 0 | 0 | 6 | 0 |
| UNCHECKABLE | 0 | 0 | 0 | 4 |

Perfect diagonal. Confident-wrong PASS on contradicted: **0**.

## Composition

3 sources × 10 claims: `news-1.md` (Indonesian news), `policy.md` (refund policy), `pricing.md` (SaaS pricing). 10 supported (light → deep paraphrase), 10 contradicted (number flips, feature mis-attribution, negation flips), 5 invented (source silent), 5 opinions.

## Notes

- Derived-number edge: "one Free and one Pro mailbox → 10,100 emails" (arithmetically true, number absent from source) lands `REVIEW` — either the detail-gate or the missing-number check demotes the `PASS`. Behavior as designed.
- First draft of that case said "a Pro user can send 10,100 emails" and the model returned `FAIL 1.00` — correctly: Pro is 10,000. The label was wrong, not the model. Case rewritten to the true derived claim.
- `FAIL` on "SAML SSO is included in Pro" came at confidence 0.78 (feature mis-attribution is the subtlest flip in the set); all number flips were 1.00.
- Threshold 0.7 needed no tuning. Bump model version → re-run this suite before trusting thresholds.
