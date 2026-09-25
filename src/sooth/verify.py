"""Build Jev questions, call the API, map answers to verdicts. Mapping is pure."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from sooth.claims import Claim

# pin: thresholds in docs are tuned against this build; bump = re-run calibration
MODEL = "jev-1.13.0"
BATCH = 30  # claims per request; 2 questions each, stays far under the 64k token cap
CHECKABLE_FLOOR = 0.5
DEFAULT_THRESHOLD = 0.7

PASS = "PASS"
FAIL = "FAIL"
REVIEW = "REVIEW"
UNCHECKABLE = "UNCHECKABLE"

DETAIL_FLOOR = 0.5  # PASS needs both supports-confidence and this detail-match probability

_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def extract_numbers(text: str) -> set[str]:
    """Number tokens in raw and separator-stripped form ('27,5' → '27,5' + '275')."""
    out: set[str] = set()
    for m in _NUM.finditer(text):
        out.add(m.group())
        out.add(m.group().replace(".", "").replace(",", ""))
    return out


def missing_numbers(claim_text: str, source_texts: list[str]) -> list[str]:
    """Claim numbers absent from every source — deterministic smuggle detector."""
    source_nums = extract_numbers(" ".join(source_texts))
    missing = []
    for m in _NUM.finditer(claim_text):
        raw = m.group()
        if raw not in source_nums and raw.replace(".", "").replace(",", "") not in source_nums:
            missing.append(raw)
    return missing


class VerifyError(Exception):
    """Config or API failure — CLI prints one line and exits 3."""


@dataclass(frozen=True)
class Verdict:
    claim_id: str
    claim_text: str
    line: int
    kind: str
    p_checkable: float | None = None
    choice: str | None = None
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float | None = None
    details_p: float | None = None
    missing_numbers: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerifyResult:
    verdicts: list[Verdict]
    model: str
    usage: dict[str, int | None]


def map_verdict(claim: Claim, p_checkable: float, choice: str, probabilities: dict[str, float],
                confidence: float, threshold: float) -> Verdict:
    """Verdict rules (PRD): checkable floor, then confidence gate, then choice."""
    if p_checkable < CHECKABLE_FLOOR:
        kind = UNCHECKABLE
    elif confidence < threshold:
        kind = REVIEW
    elif choice == "supports":
        kind = PASS
    elif choice == "contradicts":
        kind = FAIL
    else:
        kind = REVIEW  # not_found
    return Verdict(
        claim_id=claim.id,
        claim_text=claim.text,
        line=claim.line,
        kind=kind,
        p_checkable=p_checkable,
        choice=choice,
        probabilities=dict(probabilities),
        confidence=confidence,
    )


def apply_safeguards(verdict: Verdict, details_p: float | None,
                     missing: list[str]) -> Verdict:
    """Demote PASS when detail-gate is low or claim numbers are absent from sources."""
    kind = verdict.kind
    if kind == PASS and ((details_p is not None and details_p < DETAIL_FLOOR) or missing):
        kind = REVIEW
    return Verdict(
        claim_id=verdict.claim_id,
        claim_text=verdict.claim_text,
        line=verdict.line,
        kind=kind,
        p_checkable=verdict.p_checkable,
        choice=verdict.choice,
        probabilities=verdict.probabilities,
        confidence=verdict.confidence,
        details_p=details_p,
        missing_numbers=tuple(missing),
    )


def build_state(claims: list[Claim], sources: list[tuple[str, str]]) -> dict:
    return {
        "sources": [{"name": name, "text": text} for name, text in sources],
        "claims": [{"id": c.id, "text": c.text} for c in claims],
    }


def build_questions(claims: list[Claim]) -> dict:
    """Two questions per claim, fan-out in one call. Question dicts match the SDK's raw form."""
    questions: dict = {}
    for c in claims:
        questions[f"{c.id}_checkable"] = {
            "type": "noul",
            "instructions": (
                f"Statement: {c.text}\n\n"
                "Is the statement a concrete factual claim that the evidence in `sources` "
                "could support or contradict? No for opinions, vague praise, questions, "
                "or promises about the future."
            ),
        }
        questions[f"{c.id}_verdict"] = {
            "type": "choice",
            "instructions": (
                f"Statement: {c.text}\n\n"
                "Does the evidence in `sources` support the statement?"
            ),
            "criteria": {
                "supports": "The sources state or clearly imply the statement is true.",
                "contradicts": "The sources state or clearly imply the statement is false.",
                "not_found": (
                    "The sources do not address the statement either way, or the topic is absent."
                ),
            },
        }
        questions[f"{c.id}_details"] = {
            "type": "noul",
            "instructions": (
                f"Statement: {c.text}\n\n"
                "Does EVERY specific detail in the statement — names, numbers, dates, "
                "quantities, and comparisons such as 'more than' or 'about' — exactly "
                "match the evidence in `sources`? No if any detail is absent, slightly "
                "altered, or hedged differently than the sources."
            ),
        }
    return questions


def verify_claims(claims: list[Claim], sources: list[tuple[str, str]],
                  threshold: float = DEFAULT_THRESHOLD) -> VerifyResult:
    """Batch claims through Jev and return verdicts. The only network entry point."""
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise VerifyError("TYPESAFE_API_KEY not set (get a key at console.typesafe.ai)")
    try:
        from typesafe_sdk import TypeSafeClient
    except ImportError as e:  # pragma: no cover
        raise VerifyError("typesafe-sdk not installed (pip install typesafe-sdk)") from e

    verdicts: list[Verdict] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    model = MODEL
    try:
        with TypeSafeClient(model=MODEL) as client:
            for start in range(0, len(claims), BATCH):
                chunk = claims[start:start + BATCH]
                resp = client.system_one(
                    state=build_state(chunk, sources),
                    questions=build_questions(chunk),
                )
                model = resp.model
                if resp.usage:
                    usage["input_tokens"] = (usage["input_tokens"] or 0) + (resp.usage.input_tokens or 0)
                    usage["output_tokens"] = (usage["output_tokens"] or 0) + (resp.usage.output_tokens or 0)
                for c in chunk:
                    noul = resp.nouls[f"{c.id}_checkable"].noul
                    details_p = resp.nouls[f"{c.id}_details"].noul
                    ans = resp.choices[f"{c.id}_verdict"]
                    verdict = map_verdict(
                        c, noul, ans.choice, ans.probabilities, ans.confidence, threshold
                    )
                    missing = missing_numbers(c.text, [t for _, t in sources])
                    verdicts.append(apply_safeguards(verdict, details_p, missing))
    except VerifyError:
        raise
    except Exception as e:  # SDK error hierarchy; keep CLI free of SDK imports
        raise VerifyError(f"Jev call failed: {e}") from e
    return VerifyResult(verdicts=verdicts, model=model, usage=usage)
