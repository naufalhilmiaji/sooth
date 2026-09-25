"""Build Jev questions, call the API, map answers to verdicts. Mapping is pure."""

from __future__ import annotations

import os
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
                    ans = resp.choices[f"{c.id}_verdict"]
                    verdicts.append(
                        map_verdict(c, noul, ans.choice, ans.probabilities, ans.confidence, threshold)
                    )
    except VerifyError:
        raise
    except Exception as e:  # SDK error hierarchy; keep CLI free of SDK imports
        raise VerifyError(f"Jev call failed: {e}") from e
    return VerifyResult(verdicts=verdicts, model=model, usage=usage)
