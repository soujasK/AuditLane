"""
Data models shared by every stage of the pipeline:

    PR text -> Claim -> (CALL-E call) -> CallResult -> HopResult -> VerificationOutcome

Kept as plain dataclasses (no pydantic dependency) so the project has the
smallest possible install footprint for judges running it cold.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Confirmation(str, Enum):
    CONFIRMED = "confirmed"
    DENIED = "denied"
    CONDITIONAL = "conditional"
    NO_RECOLLECTION = "no_recollection"
    UNCLEAR = "unclear"


class EntailmentLabel(str, Enum):
    ENTAILMENT = "entailment"
    CONTRADICTION = "contradiction"
    NEUTRAL = "neutral"


class Verdict(str, Enum):
    VERIFIED = "verified"
    BLOCKED = "blocked"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


@dataclass
class Claim:
    """One extracted claim of undocumented verbal authorization."""

    authorizer_name: str
    claim_text: str
    subject: str
    source_line: str
    hop: int = 0  # 0 = the claim as written in the PR; 1+ = discovered mid-call
    ephemeral_challenge: Optional[str] = None


@dataclass
class CallResult:
    """Raw structured result CALL-E returns for one call (one Claim)."""

    already_covered_by_recall: bool
    authorizer_statement: str
    direct_confirmation: Confirmation
    call_duration_seconds: int
    secondary_authorizer_mentioned: Optional[str] = None
    secondary_claim_text: Optional[str] = None
    reachable: bool = True
    verbal_amendment: Optional[str] = None
    suggested_patch: Optional[str] = None
    call_uuid: str = ""
    audio_sha256: str = ""
    challenge_verified: bool = True


@dataclass
class EntailmentResult:
    label: EntailmentLabel
    confidence: float  # 0.0 - 1.0
    engine: str  # which entailment engine produced this


@dataclass
class HopResult:
    claim: Claim
    call_result: Optional[CallResult]
    entailment: Optional[EntailmentResult]

    # NOTE: these are raw signals, not the final policy decision. The
    # entailment confidence threshold is a config value, not a property
    # of the data itself, so the threshold check lives in verifier.py —
    # see ChronoAuditor._audit_claim_chain.

    @property
    def authorizer_denied(self) -> bool:
        return bool(
            self.call_result
            and self.call_result.reachable
            and self.call_result.direct_confirmation == Confirmation.DENIED
        )

    @property
    def authorizer_confirmed(self) -> bool:
        return bool(
            self.call_result
            and self.call_result.reachable
            and self.call_result.direct_confirmation == Confirmation.CONFIRMED
        )

    @property
    def entailment_is_contradiction(self) -> bool:
        return bool(self.entailment and self.entailment.label == EntailmentLabel.CONTRADICTION)

    @property
    def entailment_is_entailment(self) -> bool:
        return bool(self.entailment and self.entailment.label == EntailmentLabel.ENTAILMENT)


@dataclass
class VerificationOutcome:
    pr_reference: str
    hops: List[HopResult] = field(default_factory=list)
    verdict: Verdict = Verdict.NEEDS_HUMAN_REVIEW
    reason: str = ""
    attestation_id: Optional[str] = None
    verbal_amendment: Optional[str] = None
    suggested_patch: Optional[str] = None

    def to_markdown(self) -> str:
        lines = [f"### AuditLine verdict: `{self.verdict.value.upper()}`", "", self.reason, ""]
        for i, hop in enumerate(self.hops):
            lines.append(f"**Hop {i} — {hop.claim.authorizer_name}**")
            lines.append(f"- Claim: \"{hop.claim.claim_text}\"")
            if hop.call_result:
                lines.append(f"- Reached: {hop.call_result.reachable}")
                lines.append(f"- Their statement: \"{hop.call_result.authorizer_statement}\"")
                lines.append(f"- Confirmation: {hop.call_result.direct_confirmation.value}")
            if hop.entailment:
                lines.append(
                    f"- Entailment: {hop.entailment.label.value} "
                    f"(confidence {hop.entailment.confidence:.2f}, engine: {hop.entailment.engine})"
                )
            lines.append("")
        return "\n".join(lines)
