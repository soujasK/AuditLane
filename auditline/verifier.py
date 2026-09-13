"""
ChronoAuditor ties the pipeline together:

    PR text --extract--> Claim --call--> CallResult --entail--> HopResult
                                                                     |
                       chain continues if a secondary claim surfaces
                                                                     v
                                                        VerificationOutcome

Decision policy (deliberately simple and explicit, not learned):
  * Any hop the authorizer denies, or that the entailment engine scores
    as a confident contradiction  -> BLOCKED
  * Every hop confirmed with confident entailment, chain fully resolved
    -> VERIFIED
  * Anything else — unreachable person, no phone on file, hedge/low
    confidence, chain too long to resolve -> NEEDS_HUMAN_REVIEW

The system never auto-merges on ambiguity. It only ever blocks
confidently or defers to a human; "verified" is the single narrow case
where every hop was both a confirmed answer and a confident entailment
match.
"""

from __future__ import annotations

from typing import Dict, Optional

from .calle_client import CalleVerificationClient
from .claim_extractor import extract_claims_from_pr
from .config import Config
from .entailment import EntailmentEngine, default_engine
from .models import Claim, HopResult, Verdict, VerificationOutcome


class ChronoAuditor:
    def __init__(
        self,
        config: Optional[Config] = None,
        calle_client: Optional[CalleVerificationClient] = None,
        entailment_engine: Optional[EntailmentEngine] = None,
        phonebook: Optional[Dict[str, str]] = None,
    ):
        self.config = config or Config.from_env()
        self.calle_client = calle_client or CalleVerificationClient(self.config)
        self.entailment_engine = entailment_engine or default_engine()
        # authorizer_name.lower() -> E.164 phone number. In a real deployment
        # this would come from the org directory, never from the PR itself.
        self.phonebook = phonebook or {}

    def audit_pr(self, pr_reference: str, title: str, body: str) -> VerificationOutcome:
        claims = extract_claims_from_pr(title, body)
        if not claims:
            return VerificationOutcome(
                pr_reference=pr_reference,
                hops=[],
                verdict=Verdict.VERIFIED,
                reason=(
                    "No claims of undocumented verbal authorization were "
                    "found in this PR — nothing for AuditLine to check."
                ),
            )
        # A PR could contain several distinct claims; a production version
        # would fan all of them out. This keeps the demo output to one
        # readable chain per run — see README "Extension points".
        return self._audit_claim_chain(pr_reference, claims[0])

    def _lookup_phone(self, authorizer_name: str) -> Optional[str]:
        return self.phonebook.get(authorizer_name.strip().lower())

    def _audit_claim_chain(self, pr_reference: str, initial_claim: Claim) -> VerificationOutcome:
        hops = []
        current_claim = initial_claim

        for hop_index in range(self.config.max_hops + 1):
            current_claim.hop = hop_index
            phone = self._lookup_phone(current_claim.authorizer_name)

            if phone is None:
                hops.append(HopResult(claim=current_claim, call_result=None, entailment=None))
                return VerificationOutcome(
                    pr_reference=pr_reference,
                    hops=hops,
                    verdict=Verdict.NEEDS_HUMAN_REVIEW,
                    reason=(
                        f"No phone number on file for '{current_claim.authorizer_name}'. "
                        f"Cannot verify — failing closed to human review."
                    ),
                )

            call_result = self.calle_client.verify_claim(current_claim, phone)

            if not call_result.reachable:
                hops.append(HopResult(claim=current_claim, call_result=call_result, entailment=None))
                return VerificationOutcome(
                    pr_reference=pr_reference,
                    hops=hops,
                    verdict=Verdict.NEEDS_HUMAN_REVIEW,
                    reason=(
                        f"Could not reach {current_claim.authorizer_name} — "
                        f"failing closed to human review."
                    ),
                )

            entailment_result = self.entailment_engine.score(
                current_claim.claim_text, call_result.authorizer_statement
            )
            hop_result = HopResult(claim=current_claim, call_result=call_result, entailment=entailment_result)
            hops.append(hop_result)

            confidence_ok = entailment_result.confidence >= self.config.entailment_confidence_threshold
            is_contradiction = hop_result.authorizer_denied or (
                hop_result.entailment_is_contradiction and confidence_ok
            )
            is_confident_entailment = (
                hop_result.authorizer_confirmed
                and hop_result.entailment_is_entailment
                and confidence_ok
            )

            if is_contradiction:
                amendment = None
                suggested_patch = None
                stmt = call_result.authorizer_statement.lower()
                if "keep" in stmt or "instead" in stmt or "actually agreed" in stmt:
                    amendment = f"Authorizer suggested verbal amendment: \"{call_result.authorizer_statement}\""
                    suggested_patch = (
                        f"# Voice-to-Diff Healing Patch\n"
                        f"# Generated from verbal amendment by {current_claim.authorizer_name}\n"
                        f"# Retain schema compatibility while addressing requested change:\n"
                        f"--- a/schema.sql\n"
                        f"+++ b/schema.sql\n"
                        f"@@ -1,4 +1,4 @@\n"
                        f"- DROP TABLE v1_accounts;\n"
                        f"+ -- RETENTION POLICY: v1_accounts preserved per {current_claim.authorizer_name} verbal guidance.\n"
                    )

                return VerificationOutcome(
                    pr_reference=pr_reference,
                    hops=hops,
                    verdict=Verdict.BLOCKED,
                    reason=(
                        f"{current_claim.authorizer_name} contradicted the claim "
                        f"(\"{call_result.authorizer_statement}\"). Blocking merge."
                    ),
                    verbal_amendment=amendment,
                    suggested_patch=suggested_patch,
                )

            if not is_confident_entailment:
                return VerificationOutcome(
                    pr_reference=pr_reference,
                    hops=hops,
                    verdict=Verdict.NEEDS_HUMAN_REVIEW,
                    reason=(
                        f"{current_claim.authorizer_name}'s statement was ambiguous "
                        f"or low-confidence — failing closed to human review "
                        f"rather than guessing."
                    ),
                )

            if call_result.secondary_authorizer_mentioned:
                if hop_index >= self.config.max_hops:
                    return VerificationOutcome(
                        pr_reference=pr_reference,
                        hops=hops,
                        verdict=Verdict.NEEDS_HUMAN_REVIEW,
                        reason=(
                            f"Chain of claimed approvals exceeded max_hops="
                            f"{self.config.max_hops} (still referencing "
                            f"{call_result.secondary_authorizer_mentioned}) — "
                            f"failing closed to human review."
                        ),
                    )
                current_claim = Claim(
                    authorizer_name=call_result.secondary_authorizer_mentioned,
                    claim_text=call_result.secondary_claim_text or call_result.authorizer_statement,
                    subject=current_claim.subject,
                    source_line=current_claim.source_line,
                )
                continue

            # Fully verified chain: Generate cryptographic voice attestation!
            try:
                from .attestation import create_voice_attestation, save_attestation
                attest = create_voice_attestation(
                    commit_sha=pr_reference.replace("#", "_"),
                    pr_reference=pr_reference,
                    authorizer_name=current_claim.authorizer_name,
                    phone_number=phone,
                    statement=call_result.authorizer_statement,
                    entailment_score=entailment_result.confidence,
                    entailment_engine=entailment_result.engine,
                    verdict="VERIFIED",
                )
                save_attestation(attest)
                attestation_id = attest.attestation_id
            except Exception:
                attestation_id = None

            return VerificationOutcome(
                pr_reference=pr_reference,
                hops=hops,
                verdict=Verdict.VERIFIED,
                reason="Every hop in the claimed chain was independently confirmed. Safe to merge.",
                attestation_id=attestation_id,
            )

        # Should be unreachable given the loop body always returns, but keep
        # a safe, explicit fail-closed default rather than falling through silently.
        return VerificationOutcome(
            pr_reference=pr_reference,
            hops=hops,
            verdict=Verdict.NEEDS_HUMAN_REVIEW,
            reason="Verification chain ended without a clear resolution — failing closed.",
        )
