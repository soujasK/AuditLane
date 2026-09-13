"""
Wraps CALL-E's `client.calls.create_and_wait(...)` (see the `calle-ai`
SDK on PyPI) behind a small interface this project actually needs:
build the task prompt, build the result_schema, place the call, parse
the structured result back into a CallResult.

Real calls are opt-in, not default (see config.DRESS_REHEARSAL). In
dress rehearsal mode, MockResponder simulates CALL-E's return shape
from fixtures so the whole pipeline is runnable and testable with no
API key and no phone calls placed. See docs/SAFETY.md.
"""

from __future__ import annotations

import json
from typing import Callable, Dict, Optional

from .config import Config
from .models import CallResult, Claim, Confirmation


def build_task_prompt(claim: Claim) -> str:
    """The operational prompt handed to CALL-E as `task`.

    Methodology note: this deliberately asks for open, unprompted recall
    BEFORE reading back the specific claim. Leading with "the agent says
    you approved X, is that right?" invites a reflexive "yes" — asking
    "what did you discuss about X today?" first is what actually catches
    a fabricated claim, the same principle used in real witness-interview
    practice (free recall before recognition).
    """
    return (
        f"You are calling {claim.authorizer_name}, to independently verify "
        f"something referenced in a pull request. This is a routine "
        f"engineering change-control check, not a security incident — say "
        f"so plainly if asked.\n\n"
        f"Do NOT reveal the specific claim below until step 2.\n\n"
        f"Step 1 — Open recall: ask what they discussed or approved "
        f"recently regarding: \"{claim.subject}\". Let them answer in "
        f"their own words, unprompted.\n\n"
        f"Step 2 — Only if their open answer does not already clearly "
        f"confirm or deny the specific claim below, read it to them "
        f"directly and ask them to confirm or deny it exactly as stated:\n"
        f"  Claim: \"{claim.claim_text}\"\n\n"
        f"Capture faithfully: whether their open recall already covered "
        f"this before you had to read the claim; their statement, in "
        f"their own words; whether they confirm, deny, or have no "
        f"recollection; and if their answer references ANOTHER person's "
        f"approval (e.g. \"I was told by the security lead it was fine\"), "
        f"capture that person's name and what was said, verbatim.\n\n"
        f"Do not suggest an answer. Do not argue if they deny it — thank "
        f"them and end the call. Keep the call under three minutes."
    )


def build_result_schema() -> dict:
    return {
        "type": "object",
        "required": ["direct_confirmation", "authorizer_statement"],
        "properties": {
            "already_covered_by_recall": {"type": "boolean"},
            "authorizer_statement": {"type": "string"},
            "direct_confirmation": {
                "type": "string",
                "enum": ["confirmed", "denied", "no_recollection", "unclear"],
            },
            "secondary_authorizer_mentioned": {"type": "string"},
            "secondary_claim_text": {"type": "string"},
        },
    }


MockResponder = Callable[[Claim], Dict]


def default_mock_responses() -> Dict[str, Dict]:
    """Fixture bank keyed by authorizer_name.lower(), used when no custom
    responder is supplied. Unknown names fall back to `_UNREACHABLE`."""
    return {
        "sarah": {
            "already_covered_by_recall": False,
            "authorizer_statement": (
                "No — we actually agreed to keep v1_accounts for backward "
                "compatibility until the Q3 migration finishes."
            ),
            "direct_confirmation": "denied",
            "call_duration_seconds": 47,
        },
        "@sarah_dba": {
            "already_covered_by_recall": False,
            "authorizer_statement": (
                "No — we actually agreed to keep v1_accounts for backward "
                "compatibility until the Q3 migration finishes."
            ),
            "direct_confirmation": "denied",
            "call_duration_seconds": 52,
        },
        "the architect": {
            "already_covered_by_recall": True,
            "authorizer_statement": (
                "Yes, I verbally cleared this breaking schema change this "
                "morning — the security lead had already signed off on the "
                "access-pattern change last week, so I gave the go-ahead."
            ),
            "direct_confirmation": "confirmed",
            "call_duration_seconds": 68,
            "secondary_authorizer_mentioned": "the security lead",
            "secondary_claim_text": "the security lead already signed off on the access-pattern change",
        },
        "the security lead": {
            "already_covered_by_recall": True,
            "authorizer_statement": (
                "Yes, that's right — I already signed off on the "
                "access-pattern change last week after reviewing it, so "
                "it's confirmed on my end."
            ),
            "direct_confirmation": "confirmed",
            "call_duration_seconds": 39,
        },
    }


class CalleVerificationClient:
    """The single entry point `verifier.py` calls. Routes to a mock
    backend in dress rehearsal mode and the real SDK otherwise."""

    def __init__(self, config: Optional[Config] = None, mock_responder: Optional[MockResponder] = None):
        self.config = config or Config.from_env()
        self._mock_responder = mock_responder
        self._mock_fixtures = default_mock_responses()

    def verify_claim(self, claim: Claim, phone_number: str) -> CallResult:
        if self.config.dress_rehearsal:
            return self._mock_call(claim)
        return self._live_call(claim, phone_number)

    # -- dress rehearsal -------------------------------------------------

    def _mock_call(self, claim: Claim) -> CallResult:
        if self._mock_responder is not None:
            raw = self._mock_responder(claim)
        else:
            raw = self._mock_fixtures.get(claim.authorizer_name.strip().lower())
        if raw is None:
            return CallResult(
                already_covered_by_recall=False,
                authorizer_statement="",
                direct_confirmation=Confirmation.NO_RECOLLECTION,
                call_duration_seconds=0,
                reachable=False,
            )
        return CallResult(
            already_covered_by_recall=bool(raw.get("already_covered_by_recall", False)),
            authorizer_statement=raw.get("authorizer_statement", ""),
            direct_confirmation=Confirmation(raw.get("direct_confirmation", "unclear")),
            call_duration_seconds=int(raw.get("call_duration_seconds", 0)),
            secondary_authorizer_mentioned=raw.get("secondary_authorizer_mentioned"),
            secondary_claim_text=raw.get("secondary_claim_text"),
            reachable=True,
        )

    # -- live --------------------------------------------------------------

    def _live_call(self, claim: Claim, phone_number: str) -> CallResult:  # pragma: no cover
        try:
            from calle import CalleClient  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Live mode requires `pip install calle-ai` and a valid "
                "CALLE_API_KEY. Set AUDITLINE_DRESS_REHEARSAL=true to "
                "run without either."
            ) from exc

        if not self.config.calle_api_key:
            raise RuntimeError("CALLE_API_KEY is not set; refusing to place a real call.")

        client = CalleClient(api_key=self.config.calle_api_key, base_url=self.config.calle_base_url)
        call = client.calls.create_and_wait(
            task=build_task_prompt(claim),
            recipient={"phone": phone_number},
            result_schema=build_result_schema(),
            metadata={"authorizer": claim.authorizer_name, "hop": str(claim.hop)},
            idempotency_key=f"auditline:{claim.authorizer_name}:{abs(hash(claim.claim_text))}",
        )
        structured = call.get("structured_result") or {}
        if not structured:
            return CallResult(
                already_covered_by_recall=False,
                authorizer_statement="",
                direct_confirmation=Confirmation.NO_RECOLLECTION,
                call_duration_seconds=0,
                reachable=False,
            )
        return CallResult(
            already_covered_by_recall=bool(structured.get("already_covered_by_recall", False)),
            authorizer_statement=structured.get("authorizer_statement", ""),
            direct_confirmation=Confirmation(structured.get("direct_confirmation", "unclear")),
            call_duration_seconds=self.config.max_call_duration_seconds,
            secondary_authorizer_mentioned=structured.get("secondary_authorizer_mentioned"),
            secondary_claim_text=structured.get("secondary_claim_text"),
            reachable=True,
        )
