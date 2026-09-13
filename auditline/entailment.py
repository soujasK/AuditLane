"""
Compares the agent's claim ("Sarah confirmed dropping v1_accounts is
fine") against what the authorizer actually said on the phone, and
labels the pair as entailment / contradiction / neutral.

Two engines are provided behind the same interface:

  * HeuristicEntailmentEngine — zero dependencies, zero downloads, fully
    offline. This is the default, and what CI/tests/dress-rehearsal use.
    It is a deliberately simple negation- and overlap-based approximation,
    not a claim of state-of-the-art NLI performance.

  * TransformerEntailmentEngine — an optional, higher-quality engine using
    a pretrained NLI model via the `transformers` library (e.g.
    roberta-large-mnli). This requires `pip install transformers torch`
    and network access to download model weights, which is NOT assumed
    to be available in every judging environment, so it is opt-in, not
    the default. See README "Swapping in a real NLI model".

Both return an EntailmentResult with the same shape, so `verifier.py`
never needs to know which one is active.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from .models import EntailmentLabel, EntailmentResult

_NEGATION_WORDS = {
    "not", "no", "never", "n't", "didn't", "did not", "wasn't", "was not",
    "isn't", "is not", "wouldn't", "wouldn't", "doesn't", "does not",
    "false", "incorrect", "wrong", "denied", "refuse", "refused",
}

_HEDGE_WORDS = {
    "maybe", "perhaps", "not sure", "unsure", "i think", "possibly",
    "don't recall", "do not recall", "don't remember", "no idea",
    "can't confirm", "cannot confirm",
}

_STOPWORDS = {
    "the", "a", "an", "is", "was", "are", "were", "to", "of", "in", "on",
    "for", "with", "that", "this", "and", "or", "it", "as", "be", "by",
    "we", "i", "you", "he", "she", "they", "at", "during",
}


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _contains_any(text_lower: str, phrases: set) -> bool:
    return any(phrase in text_lower for phrase in phrases)


class EntailmentEngine(ABC):
    name: str = "abstract"

    @abstractmethod
    def score(self, claim_text: str, statement_text: str) -> EntailmentResult:
        raise NotImplementedError


class HeuristicEntailmentEngine(EntailmentEngine):
    """
    Rule-based approximation of NLI, tuned for this project's narrow use
    case: comparing a short authorization claim against a short spoken
    statement, not general-purpose textual entailment.

    Logic, in order:
      1. If the statement hedges ("not sure", "don't recall"...) -> neutral,
         low confidence. We never want a hedge to read as confirmation.
      2. Compute lexical overlap between claim and statement (shared
         non-stopword tokens over the smaller token set).
      3. If overlap is high AND the statement carries a negation the claim
         doesn't -> contradiction (the person is denying the same topic
         the claim is about).
      4. If overlap is high AND no negation mismatch -> entailment.
      5. Otherwise -> neutral (statement doesn't clearly address the
         claim either way — this is intentionally the default; fail
         closed to human review rather than guess).
    """

    name = "heuristic-v1"

    def score(self, claim_text: str, statement_text: str) -> EntailmentResult:
        statement_lower = statement_text.lower()

        if _contains_any(statement_lower, _HEDGE_WORDS):
            return EntailmentResult(EntailmentLabel.NEUTRAL, 0.55, self.name)

        claim_tokens = _tokenize(claim_text)
        statement_tokens = _tokenize(statement_text)
        if not claim_tokens or not statement_tokens:
            return EntailmentResult(EntailmentLabel.NEUTRAL, 0.5, self.name)

        overlap = claim_tokens & statement_tokens
        smaller = min(len(claim_tokens), len(statement_tokens))
        overlap_ratio = len(overlap) / smaller if smaller else 0.0

        claim_negated = _contains_any(claim_text.lower(), _NEGATION_WORDS)
        statement_negated = _contains_any(statement_lower, _NEGATION_WORDS)
        negation_mismatch = statement_negated != claim_negated

        if overlap_ratio >= 0.35:
            if negation_mismatch:
                confidence = min(0.95, 0.6 + overlap_ratio * 0.4)
                return EntailmentResult(EntailmentLabel.CONTRADICTION, confidence, self.name)
            confidence = min(0.9, 0.55 + overlap_ratio * 0.4)
            return EntailmentResult(EntailmentLabel.ENTAILMENT, confidence, self.name)

        return EntailmentResult(EntailmentLabel.NEUTRAL, 0.5, self.name)


class TransformerEntailmentEngine(EntailmentEngine):
    """
    Optional higher-quality engine backed by a pretrained NLI model.
    Not used unless explicitly constructed and successfully loaded —
    import and model download happen lazily so importing this module
    never requires `transformers` to be installed.
    """

    name = "transformer-mnli"

    def __init__(self, model_name: str = "roberta-large-mnli"):
        try:
            from transformers import pipeline  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised only when extra installed
            raise RuntimeError(
                "TransformerEntailmentEngine requires `pip install transformers torch` "
                "plus network access to download model weights. Fall back to "
                "HeuristicEntailmentEngine if that isn't available."
            ) from exc
        self._pipe = pipeline("text-classification", model=model_name, top_k=None)

    def score(self, claim_text: str, statement_text: str) -> EntailmentResult:  # pragma: no cover
        # MNLI convention: premise = what we know happened, hypothesis = claim to check.
        pair_input = f"{statement_text} </s></s> {claim_text}"
        results = self._pipe(pair_input)[0]
        best = max(results, key=lambda r: r["score"])
        label_map = {
            "ENTAILMENT": EntailmentLabel.ENTAILMENT,
            "CONTRADICTION": EntailmentLabel.CONTRADICTION,
            "NEUTRAL": EntailmentLabel.NEUTRAL,
        }
        label = label_map.get(best["label"].upper(), EntailmentLabel.NEUTRAL)
        return EntailmentResult(label, float(best["score"]), self.name)


def default_engine() -> EntailmentEngine:
    return HeuristicEntailmentEngine()
