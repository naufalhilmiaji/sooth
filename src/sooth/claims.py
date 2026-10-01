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
_HAS_DIGIT = re.compile(r"\d")


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    line: int


@dataclass(frozen=True)
class Segment:
    """A source sentence — an evidence candidate."""
    id: str
    text: str
    line: int
    source: str


def _scan(text: str) -> tuple[list[tuple[int, str]], list[str]]:
    """(kept, dropped) sentences — shared by claim and segment splitting.

    A sentence is dropped only when it is not claim-shaped: a question, or a fragment
    with no number in it. Short sentences that carry a digit are kept — `It cost $2M.`
    is three words and a claim, and dropping it would hide a checkable statement.
    """
    kept: list[tuple[int, str]] = []
    dropped: list[str] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if _HEADING.match(raw):
            continue
        line = _BULLET.sub("", raw).strip()
        if not line or _BOLD_ONLY.match(line):
            continue
        line = line.replace("**", "")
        for sentence in _SENTENCE_SPLIT.split(line):
            s = sentence.strip()
            if not s:
                continue
            if s.endswith("?") or (len(s.split()) < _MIN_WORDS and not _HAS_DIGIT.search(s)):
                dropped.append(s)
                continue
            kept.append((lineno, s))
    return kept, dropped


def _iter_sentences(text: str) -> list[tuple[int, str]]:
    """(line_no, sentence) pairs — the kept half of `_scan`."""
    return _scan(text)[0]


def dropped_sentences(text: str) -> list[str]:
    """Sentences skipped as non-claims. Surfaced so nothing disappears silently."""
    return _scan(text)[1]


def split_claims(text: str) -> list[Claim]:
    """Return checkable-looking sentences as claims. Skips headings, questions, fragments."""
    return [Claim(id=f"c{i + 1}", text=s, line=ln)
            for i, (ln, s) in enumerate(_iter_sentences(text))]


def split_segments(text: str, source: str, start_index: int = 1) -> list[Segment]:
    """Source sentences as evidence candidates. Ids continue from start_index (s{n})."""
    return [Segment(id=f"s{start_index + i}", text=s, line=ln, source=source)
            for i, (ln, s) in enumerate(_iter_sentences(text))]
