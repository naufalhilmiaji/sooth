"""Render verdicts to text and build the JSONL log record. Pure functions."""

from __future__ import annotations

from sooth.verify import FAIL, PASS, REVIEW, UNCHECKABLE, Verdict, VerifyResult

_BAR_WIDTH = 8
_MARK = {PASS: "✅ PASS", FAIL: "❌ FAIL", REVIEW: "⚠️ REVIEW", UNCHECKABLE: "➖ UNCHECKABLE"}
_PLAIN = {PASS: "PASS", FAIL: "FAIL", REVIEW: "REVIEW", UNCHECKABLE: "UNCHECKABLE"}


def bar(p: float, width: int = _BAR_WIDTH) -> str:
    filled = round(p * width)
    return "█" * filled + "░" * (width - filled)


def _why(v: Verdict) -> str:
    if v.kind == UNCHECKABLE:
        return f"P(checkable)={v.p_checkable:.2f}"
    parts = []
    if v.probabilities:
        parts.append(" / ".join(f"{k} {p:.2f}" for k, p in v.probabilities.items()))
    if v.details_p is not None and v.details_p < 1.0:
        parts.append(f"details {v.details_p:.2f}")
    if v.missing_numbers:
        parts.append("missing #s: " + ", ".join(v.missing_numbers))
    return " · ".join(parts)


def _p(v: Verdict) -> float:
    return v.p_checkable if v.kind == UNCHECKABLE else (v.confidence or 0.0)


def counts(verdicts: list[Verdict]) -> dict[str, int]:
    tallies = {PASS: 0, FAIL: 0, REVIEW: 0, UNCHECKABLE: 0}
    for v in verdicts:
        tallies[v.kind] += 1
    return tallies


def _evidence(v: Verdict) -> str:
    if not v.evidence_text:
        return ""
    snippet = v.evidence_text if len(v.evidence_text) <= 60 else v.evidence_text[:57] + "…"
    return f'`{v.evidence_source}:{v.evidence_line}` "{snippet}"'


def render_markdown(verdicts: list[Verdict], threshold: float) -> str:
    t = counts(verdicts)
    lines = [
        f"# Sooth\n",
        f"**PASS {t[PASS]} · FAIL {t[FAIL]} · REVIEW {t[REVIEW]} · UNCHECKABLE {t[UNCHECKABLE]}**"
        f" — threshold {threshold:.2f}\n",
        "| # | Claim | Verdict | P | Why (P distribution) | Evidence |",
        "|---|-------|---------|---|----------------------|----------|",
    ]
    for i, v in enumerate(verdicts, start=1):
        claim = v.claim_text.replace("|", "\\|")
        lines.append(f"| {i} | {claim} | {_MARK[v.kind]} | {bar(_p(v))} {_p(v):.2f} | {_why(v)} | {_evidence(v)} |")
    needs = [v for v in verdicts if v.kind in (REVIEW, UNCHECKABLE)]
    if needs:
        lines += ["\n## Needs review\n"]
        lines += [f"- line {v.line}: {v.claim_text}" for v in needs]
    return "\n".join(lines) + "\n"


def render_plain(verdicts: list[Verdict], threshold: float) -> str:
    t = counts(verdicts)
    lines = [
        (
            f"PASS {t[PASS]}  FAIL {t[FAIL]}  REVIEW {t[REVIEW]}  UNCHECKABLE {t[UNCHECKABLE]}"
            f"  (threshold {threshold:.2f})"
        )
    ]
    for v in verdicts:
        lines.append(f"{_PLAIN[v.kind]:<11} {_p(v):.2f}  line {v.line}  {v.claim_text}")
    return "\n".join(lines) + "\n"


def exit_code(verdicts: list[Verdict]) -> int:
    """0 clean, 1 any FAIL, 2 any REVIEW (no FAIL). UNCHECKABLE never fails CI."""
    kinds = {v.kind for v in verdicts}
    if FAIL in kinds:
        return 1
    if REVIEW in kinds:
        return 2
    return 0


def log_record(result: VerifyResult, threshold: float, sources: list[str], draft: str) -> dict:
    """One JSONL line per run. Full probability distributions — the decision-ledger seed."""
    return {
        "model": result.model,
        "threshold": threshold,
        "sources": sources,
        "draft": draft,
        "usage": dict(result.usage),
        "results": [
            {
                "id": v.claim_id,
                "text": v.claim_text,
                "line": v.line,
                "kind": v.kind,
                "p_checkable": v.p_checkable,
                "choice": v.choice,
                "probabilities": dict(v.probabilities),
                "confidence": v.confidence,
                "details_p": v.details_p,
                "missing_numbers": list(v.missing_numbers),
                "evidence": (
                    {
                        "id": v.evidence_id,
                        "text": v.evidence_text,
                        "line": v.evidence_line,
                        "source": v.evidence_source,
                    }
                    if v.evidence_text
                    else None
                ),
            }
            for v in result.verdicts
        ],
    }
