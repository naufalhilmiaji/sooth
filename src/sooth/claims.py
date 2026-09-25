"""Split draft text into claims. Pure functions, no I/O."""

from __future__ import annotations

import re
from dataclasses import dataclass

# ponytail: regex splitter — mis-splits abbreviations/quotes; upgrade to clause-level when real drafts demand
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
_BOLD_ONLY = re.compile(r"^\*\*[^*]+\*\*:?\s*$")  # **Label** or **Label:** — heading, not a claim
_MIN_WORDS = 4


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    line: int


def split_claims(text: str) -> list[Claim]:
    """Return checkable-looking sentences as claims. Skips headings, questions, fragments."""
    claims: list[Claim] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if _HEADING.match(raw):
            continue
        line = _BULLET.sub("", raw).strip()
        if not line or _BOLD_ONLY.match(line):
            continue
        line = line.replace("**", "")  # keep text of **Label:** claim, drop emphasis
        if not line:
            continue
        for sentence in _SENTENCE_SPLIT.split(line):
            s = sentence.strip()
            if not s or s.endswith("?"):
                continue
            if len(s.split()) < _MIN_WORDS:
                continue
            claims.append(Claim(id=f"c{len(claims) + 1}", text=s, line=lineno))
    return claims
