"""
Extracts claims of undocumented, verbal human authorization from PR
descriptions and commit messages.

Deliberately rule-based, not an LLM call: it needs zero external API
access, so the whole pipeline runs and is testable completely offline.
Swapping in an LLM-based extractor for higher recall on messier phrasing
is a natural extension point (see README "Extension points").

Scope, on purpose: this only looks for claims of the form "a named person
verbally said X was fine" — the one category of claim that has no digital
record to check against by definition. It is not trying to fact-check
code, tests, or anything with an existing paper trail.
"""

from __future__ import annotations

import re
from typing import List

from .models import Claim

_ROLE_WORDS = "lead|admin|administrator|architect|owner|manager|engineer|dba"

_TRIGGER_WORDS_AFTER = [
    "confirmed",
    "cleared",
    "verified",
    "approved",
    "authorized",
    "discussed",
    "signed off",
    "verbally cleared",
    "ok'd",
    "okayed",
    "got the go-ahead from",
]
_TRIGGER_WORDS_BEFORE = [
    "said",
    "confirmed",
    "approved",
    "cleared",
    "verbally cleared",
    "gave the go-ahead",
    "signed off",
    "ok'd",
    "okayed",
    "already knows",
]


def _case_insensitive_first_letter(word: str) -> str:
    """Turn 'confirmed' into '[cC]onfirmed' so we can match sentence-start
    capitalization without a blanket IGNORECASE flag, which would also
    make our [A-Z] name-detection match lowercase words."""
    if not word or not word[0].isalpha():
        return re.escape(word)
    first, rest = word[0], word[1:]
    return f"[{first.lower()}{first.upper()}]{re.escape(rest)}"


_TRIGGER_AFTER_RE = "|".join(_case_insensitive_first_letter(w) for w in _TRIGGER_WORDS_AFTER)
_TRIGGER_BEFORE_RE = "|".join(_case_insensitive_first_letter(w) for w in _TRIGGER_WORDS_BEFORE)

_NAME_CAPTURE = (
    r"(@[\w-]+"
    r"|[Tt]he\s+(?:[a-z]+\s+){0,3}(?:" + _ROLE_WORDS + r")"
    r"|[A-Z][\w'\u2019-]*(?:\s+[A-Z][\w'\u2019-]*){0,1})"
)

PATTERN_A = re.compile(r"(?:" + _TRIGGER_AFTER_RE + r")\s+(?:with|by|from)\s+" + _NAME_CAPTURE)
PATTERN_B = re.compile(_NAME_CAPTURE + r"\s+(?:" + _TRIGGER_BEFORE_RE + r")")

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")
_SINGLE_NEWLINE = re.compile(r"(?<!\n)\n(?!\n)")


def _normalize_whitespace(text: str) -> str:
    """Markdown PR bodies wrap long sentences across single newlines —
    those are not sentence boundaries, only blank-line paragraph breaks
    are. Collapse the former to spaces before splitting on sentences."""
    return _SINGLE_NEWLINE.sub(" ", text)


_NON_NAME_WORDS = {
    "as", "this", "that", "it", "so", "also", "then", "once", "after",
    "the", "a", "an", "we", "i", "they", "he", "she", "you", "but",
    "and", "or", "if", "when", "while", "before", "since", "because",
    "however", "additionally", "note", "fixes", "closes", "resolves",
}


def _looks_like_a_name(candidate: str) -> bool:
    candidate = candidate.strip().rstrip(".,;:")
    if not candidate:
        return False
    if candidate.startswith("@"):
        return True
    lowered = candidate.lower()
    if lowered in _NON_NAME_WORDS:
        # Rejects sentence-initial capitalized filler words ("As confirmed...",
        # "This confirmed...") that PATTERN_B would otherwise mistake for a name.
        return False
    if candidate[0].isupper():
        return True
    if lowered.startswith("the ") and any(
        f" {role}" in f" {lowered}" or lowered.endswith(role)
        for role in _ROLE_WORDS.split("|")
    ):
        return True
    return False


def extract_claims(text: str, default_subject: str = "") -> List[Claim]:
    """Scan text for sentence-level claims of undocumented verbal
    authorization. Returns one Claim per matched sentence+name pair."""
    claims: List[Claim] = []
    if not text:
        return claims

    seen = set()
    for raw_sentence in _SENTENCE_SPLIT.split(_normalize_whitespace(text)):
        sentence = raw_sentence.strip()
        if not sentence:
            continue
        for pattern in (PATTERN_A, PATTERN_B):
            for match in pattern.finditer(sentence):
                name = match.group(1).strip().rstrip(".,;:")
                if not _looks_like_a_name(name):
                    continue
                key = (name.lower(), sentence.lower())
                if key in seen:
                    continue
                seen.add(key)
                claims.append(
                    Claim(
                        authorizer_name=name,
                        claim_text=sentence,
                        subject=default_subject or sentence,
                        source_line=sentence,
                    )
                )
    return claims


def extract_claims_from_pr(title: str, body: str) -> List[Claim]:
    """Convenience wrapper: use the PR title as the fallback 'subject'
    when a claim sentence doesn't carry enough context on its own."""
    return extract_claims(body or "", default_subject=title or "")
