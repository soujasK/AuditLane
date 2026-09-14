from auditlane.calle_client import CalleVerificationClient
from auditlane.config import Config
from auditlane.entailment import HeuristicEntailmentEngine
from auditlane.models import Verdict
from auditlane.verifier import AuditLaneVerifier

PHONEBOOK = {
    "sarah": "+15550001111",
    "@sarah_dba": "+15550001111",
    "the architect": "+15550002222",
    "the security lead": "+15550003333",
}


def make_auditor(mock_responder=None, max_hops=2):
    config = Config(dress_rehearsal=True, max_hops=max_hops)
    calle_client = CalleVerificationClient(config=config, mock_responder=mock_responder)
    return AuditLaneVerifier(
        config=config,
        calle_client=calle_client,
        entailment_engine=HeuristicEntailmentEngine(),
        phonebook=PHONEBOOK,
    )


def test_no_claims_is_verified_trivially():
    auditor = make_auditor()
    outcome = auditor.audit_pr("pr#1", "Rename a variable", "No behavior change, just a rename.")
    assert outcome.verdict == Verdict.VERIFIED
    assert outcome.hops == []


def test_no_phone_on_file_fails_closed():
    auditor = make_auditor()
    outcome = auditor.audit_pr(
        "pr#2",
        "Drop legacy table",
        "Confirmed with Random Person that this is fine.",
    )
    assert outcome.verdict == Verdict.NEEDS_HUMAN_REVIEW
    assert "No phone number on file" in outcome.reason


def test_denial_blocks_the_merge():
    def responder(claim):
        return {
            "already_covered_by_recall": False,
            "authorizer_statement": "No, I never approved dropping v1_accounts, we're keeping it.",
            "direct_confirmation": "denied",
            "call_duration_seconds": 40,
        }

    auditor = make_auditor(mock_responder=responder)
    outcome = auditor.audit_pr(
        "pr#3",
        "Drop legacy table",
        "Confirmed with Sarah that dropping v1_accounts is fine.",
    )
    assert outcome.verdict == Verdict.BLOCKED
    assert len(outcome.hops) == 1


def test_confident_confirmation_verifies():
    def responder(claim):
        return {
            "already_covered_by_recall": True,
            "authorizer_statement": "Yes, dropping v1_accounts is fine, I confirmed that this morning.",
            "direct_confirmation": "confirmed",
            "call_duration_seconds": 30,
        }

    auditor = make_auditor(mock_responder=responder)
    outcome = auditor.audit_pr(
        "pr#4",
        "Drop legacy table",
        "Confirmed with Sarah that dropping v1_accounts is fine.",
    )
    assert outcome.verdict == Verdict.VERIFIED
    assert len(outcome.hops) == 1


def test_unreachable_authorizer_fails_closed():
    def responder(claim):
        return None

    auditor = make_auditor(mock_responder=responder)
    outcome = auditor.audit_pr(
        "pr#5",
        "Drop legacy table",
        "Confirmed with Sarah that dropping v1_accounts is fine.",
    )
    assert outcome.verdict == Verdict.NEEDS_HUMAN_REVIEW
    assert "Could not reach" in outcome.reason


def test_multi_hop_chain_resolves_to_verified():
    # Uses the built-in fixture bank: "the architect" confirms but names
    # "the security lead" as a secondary source, who independently confirms.
    auditor = make_auditor()  # default fixtures, no custom responder
    outcome = auditor.audit_pr(
        "pr#6",
        "Change access pattern",
        "The architect verbally cleared this breaking schema change.",
    )
    assert outcome.verdict == Verdict.VERIFIED
    assert len(outcome.hops) == 2
    assert outcome.hops[1].claim.authorizer_name == "the security lead"


def test_multi_hop_chain_exceeding_max_hops_fails_closed():
    auditor = make_auditor(max_hops=0)  # not enough hops to reach "the security lead"
    outcome = auditor.audit_pr(
        "pr#7",
        "Change access pattern",
        "The architect verbally cleared this breaking schema change.",
    )
    assert outcome.verdict == Verdict.NEEDS_HUMAN_REVIEW
    assert "exceeded max_hops" in outcome.reason
