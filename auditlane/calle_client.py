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

import hashlib
import json
import os
from pathlib import Path
from typing import Callable, Dict, Optional

from .config import Config
from .models import CallResult, Claim, Confirmation

# Local, on-disk ledger of live calls actually placed — see
# CalleVerificationClient._check_and_record_call_budget. Gitignored;
# delete it (or bump AUDITLANE_MAX_LIVE_CALLS) to reset after topping up.
#
# Deliberately NOT a bare relative path (that was the bug: it used to be
# Path(".auditlane_call_budget.json"), which resolves against whatever
# the CURRENT PROCESS's working directory happens to be. The hook is
# specifically meant to be invoked from OTHER projects' directories
# (that's the whole point of a portable gate) — so every real call
# placed from e.g. a "shopfast" Claude Code session was silently
# writing (and reading) this file inside shopfast instead of here,
# meaning the guard was tracking a budget that reset itself per-project
# instead of a real global cap. Anchored to this file's own location
# instead, same fix already applied to LEDGER_PATH in ledger.py, with
# the same AUDITLANE_CALL_BUDGET_PATH env override for tests.
_ROOT_DIR = Path(__file__).resolve().parents[1]
_CALL_BUDGET_FILE = (
    Path(os.environ["AUDITLANE_CALL_BUDGET_PATH"])
    if os.environ.get("AUDITLANE_CALL_BUDGET_PATH")
    else _ROOT_DIR / ".auditlane_call_budget.json"
)


def _stable_claim_hash(claim_text: str) -> str:
    """Deterministic hash for idempotency keys.

    Python's builtin hash() is salted per-process (PYTHONHASHSEED) for
    security, so the same claim text produces a DIFFERENT idempotency
    key every time the process restarts. That defeats the entire point
    of idempotency: if a request round-trip fails after CALL-E already
    created the call (a timeout on our end, a crashed retry, a re-run of
    the same command), the retry gets treated as a brand-new request
    instead of being deduplicated — a real, silent way for live-call
    credits to leak. sha256 of the claim text is stable across runs.
    """
    return hashlib.sha256(claim_text.encode("utf-8")).hexdigest()[:16]


def build_task_prompt(claim: Claim, max_call_seconds: int = 180) -> str:
    """The operational prompt handed to CALL-E as `task`.

    Methodology note: this deliberately asks for open, unprompted recall
    BEFORE reading back the specific claim. Leading with "the agent says
    you approved X, is that right?" invites a reflexive "yes" — asking
    "what did you discuss about X today?" first is what actually catches
    a fabricated claim, the same principle used in real witness-interview
    practice (free recall before recognition).

    `max_call_seconds` is threaded in from Config.max_call_duration_seconds
    so the prompt's stated time budget actually matches what the caller
    configured, instead of a hardcoded "three minutes" the config couldn't
    change. Step 0 exists because a live call burned most of a 3-minute
    budget stuck confirming identity on a noisy connection before ever
    reaching the real question — this makes the bot move on after ANY
    plausible affirmative instead of re-asking.
    """
    minutes = max(1, round(max_call_seconds / 60))
    return (
        f"You are calling {claim.authorizer_name}, to independently verify "
        f"something referenced in a pull request. This is a routine "
        f"engineering change-control check, not a security incident — say "
        f"so plainly if asked.\n\n"
        f"Do NOT reveal the specific claim below until step 2.\n\n"
        f"Step 0 — Identify the person quickly: ask once if you're "
        f"speaking with {claim.authorizer_name}. On ANY plausible "
        f"affirmative (\"yes\", \"speaking\", \"that's me\", or them simply "
        f"answering as themselves) move on immediately to Step 1 — do NOT "
        f"re-ask or re-confirm identity again during this call, even if "
        f"the connection is noisy or an earlier answer was unclear. If "
        f"they explicitly say they are someone else, politely end the "
        f"call. Spend at most 30 seconds on this step.\n\n"
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
        f"them and end the call. Reaching Step 1's open-recall question "
        f"is the priority — get there fast. Keep the whole call under "
        f"{minutes} minute{'s' if minutes != 1 else ''}."
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


# E.164 country calling code -> ISO 3166-1 alpha-2, used to populate the
# `region` field CALL-E's recipient schema documents as "used for routing
# and compliance checks" (see https://docs.heycall-e.com/#/api-reference
# and every example in CALL-E's own SDK repo, which always sets `region`
# and `locale` — never omits them). Leaving `region` unset appears to
# cause calls to non-US numbers to fail fast (bot-side hangup, 0s
# duration, "NO ANSWER") before ever reaching the handset — see
# docs/SAFETY.md troubleshooting notes. Longest-prefix-first since ITU
# calling codes are prefix-free; not exhaustive, just common destinations.
_COUNTRY_CALLING_CODES: Dict[str, str] = {
    "1": "US", "7": "RU",
    "20": "EG", "27": "ZA", "30": "GR", "31": "NL", "32": "BE", "33": "FR",
    "34": "ES", "36": "HU", "39": "IT", "40": "RO", "41": "CH", "43": "AT",
    "44": "GB", "45": "DK", "46": "SE", "47": "NO", "48": "PL", "49": "DE",
    "51": "PE", "52": "MX", "53": "CU", "54": "AR", "55": "BR", "56": "CL",
    "57": "CO", "58": "VE", "60": "MY", "61": "AU", "62": "ID", "63": "PH",
    "64": "NZ", "65": "SG", "66": "TH", "81": "JP", "82": "KR", "84": "VN",
    "86": "CN", "90": "TR", "91": "IN", "92": "PK", "93": "AF", "94": "LK",
    "95": "MM", "98": "IR",
    "212": "MA", "213": "DZ", "216": "TN", "218": "LY", "220": "GM",
    "233": "GH", "234": "NG", "254": "KE", "255": "TZ", "256": "UG",
    "351": "PT", "352": "LU", "353": "IE", "354": "IS", "358": "FI",
    "420": "CZ", "421": "SK", "852": "HK", "853": "MO", "855": "KH",
    "856": "LA", "880": "BD", "886": "TW", "960": "MV", "961": "LB",
    "962": "JO", "963": "SY", "964": "IQ", "965": "KW", "966": "SA",
    "967": "YE", "968": "OM", "970": "PS", "971": "AE", "972": "IL",
    "973": "BH", "974": "QA", "975": "BT", "976": "MN", "977": "NP",
    "992": "TJ", "993": "TM", "994": "AZ", "995": "GE", "996": "KG",
    "998": "UZ",
}

# Region -> a reasonable default locale to hand CALL-E for that recipient.
# Best-effort; falls back to "en-US" for anything not listed here.
_REGION_LOCALES: Dict[str, str] = {
    "IN": "en-IN", "GB": "en-GB", "AU": "en-AU", "US": "en-US", "CA": "en-CA",
}


def _recipient_region(phone_number: str) -> Optional[str]:
    """Best-effort ISO region for an E.164 number, for CALL-E's routing."""
    digits = phone_number.lstrip("+")
    for length in (3, 2, 1):
        code = _COUNTRY_CALLING_CODES.get(digits[:length])
        if code:
            return code
    return None


def build_recipient(phone_number: str) -> Dict[str, Optional[str]]:
    """Build the recipient payload CALL-E's docs/examples actually use —
    `phone`, `region`, and `locale` — instead of a bare phone number."""
    region = _recipient_region(phone_number)
    return {
        "phone": phone_number,
        "region": region,
        "locale": _REGION_LOCALES.get(region, "en-US") if region else None,
    }


MockResponder = Callable[[Claim], Dict]


def default_mock_responses() -> Dict[str, Dict]:
    """Fixture bank keyed by authorizer_name.lower(), used when no custom
    responder is supplied. Unknown names fall back to `_UNREACHABLE`."""
    return {
        "soujas": {
            "already_covered_by_recall": False,
            "authorizer_statement": (
                "No — I don't think that's right, let's hold off on that "
                "until we've double-checked it's actually safe to remove."
            ),
            "direct_confirmation": "denied",
            "call_duration_seconds": 44,
        },
        "@soujas": {
            "already_covered_by_recall": False,
            "authorizer_statement": (
                "No — I don't think that's right, let's hold off on that "
                "until we've double-checked it's actually safe to remove."
            ),
            "direct_confirmation": "denied",
            "call_duration_seconds": 44,
        },
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

    # -- call budget guardrail -------------------------------------------
    # Deliberately a local file, not just "remember to check" — see
    # config.max_live_calls. Only _live_call touches this; dress
    # rehearsal never does, since it never spends anything real.

    def _read_call_count(self) -> int:
        if not _CALL_BUDGET_FILE.exists():
            return 0
        try:
            data = json.loads(_CALL_BUDGET_FILE.read_text(encoding="utf-8"))
            return int(data.get("live_calls_placed", 0))
        except Exception:
            return 0

    def _enforce_call_budget(self) -> None:
        placed = self._read_call_count()
        if placed >= self.config.max_live_calls:
            raise RuntimeError(
                f"Local call budget reached: {placed}/{self.config.max_live_calls} live "
                f"calls already placed (tracked in {_CALL_BUDGET_FILE}). This is a "
                f"deliberate guardrail, not a CALL-E error — it exists so a retry loop "
                f"or an accidental re-run can't quietly spend more trial credits. To "
                f"place another real call: raise AUDITLANE_MAX_LIVE_CALLS, or delete "
                f"{_CALL_BUDGET_FILE} after topping up / rotating your API key."
            )

    def _record_call_placed(self, call_id: Optional[str]) -> None:
        placed = self._read_call_count() + 1
        _CALL_BUDGET_FILE.write_text(
            json.dumps(
                {"live_calls_placed": placed, "last_call_id": call_id},
                indent=2,
            ),
            encoding="utf-8",
        )

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

    def _require_live_client(self):  # pragma: no cover
        try:
            from calle import CalleClient  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Live mode requires `pip install calle-ai` and a valid "
                "CALLE_API_KEY. Set AUDITLANE_DRESS_REHEARSAL=true to "
                "run without either."
            ) from exc
        if not self.config.calle_api_key:
            raise RuntimeError("CALLE_API_KEY is not set; refusing to place a real call.")
        return CalleClient(api_key=self.config.calle_api_key, base_url=self.config.calle_base_url)

    def start_live_call(self, claim: Claim, phone_number: str) -> str:  # pragma: no cover
        """Creates a real CALL-E call and returns its id immediately,
        without waiting for it to finish — lets a caller poll
        `get_call_events`/`get_call_status` for a live-updating transcript
        instead of blocking silently for however long the call takes.
        `_live_call` below is built on top of this, so the budget guard
        and idempotency key can never drift between the two paths."""
        client = self._require_live_client()
        self._enforce_call_budget()

        # create() (not create_and_wait) so the local budget ledger is
        # only incremented once CALL-E has actually confirmed a call
        # exists — i.e. once a real credit is genuinely at stake. A
        # create() that gets rejected (e.g. insufficient_balance) raises
        # before this point and never touches the ledger.
        call = client.calls.create(
            task=build_task_prompt(claim, max_call_seconds=self.config.max_call_duration_seconds),
            recipient=build_recipient(phone_number),
            result_schema=build_result_schema(),
            metadata={"authorizer": claim.authorizer_name, "hop": str(claim.hop)},
            idempotency_key=f"auditlane:{claim.authorizer_name}:{_stable_claim_hash(claim.claim_text)}",
        )
        real_call_id = str(call["id"])
        self._record_call_placed(real_call_id)
        return real_call_id

    def get_call_status(self, call_id: str) -> dict:  # pragma: no cover
        """Raw CALL-E call object — status, and once terminal,
        structured_result / recipients / transcript_turns."""
        return self._require_live_client().calls.get(call_id)

    def get_call_events(self, call_id: str, cursor: Optional[str] = None) -> dict:  # pragma: no cover
        """Raw CALL-E event log for one call — includes "Bot is speaking:
        ..." / "Callee said: ..." lines as they actually happen. Pass the
        previous response's next_cursor to fetch only new events."""
        return self._require_live_client().calls.list_events(call_id, cursor=cursor)

    def parse_call_result(self, call: dict) -> CallResult:  # pragma: no cover
        """Turns a raw (terminal-state) CALL-E call object into our
        CallResult model — shared by the blocking `_live_call` path and
        any streaming caller polling `get_call_status` to termination,
        so the two can never parse a result differently."""
        real_call_id = str(call.get("id", ""))
        structured = call.get("structured_result") or {}

        # Real transcript, when CALL-E returned one, hashed for the
        # attestation layer — CALL-E's API exposes transcript text, not
        # raw audio, so this is a transcript hash, not literally an
        # "audio" hash; still tied to what was actually said on this
        # specific real_call_id instead of being synthesized locally.
        transcript_text = "\n".join(
            f"{turn.get('speaker', '')}:{turn.get('text', '')}"
            for recipient in call.get("recipients", [])
            for attempt in recipient.get("attempts", [])
            for turn in attempt.get("transcript_turns", [])
        )
        transcript_hash = hashlib.sha256(transcript_text.encode("utf-8")).hexdigest() if transcript_text else ""

        if not structured:
            return CallResult(
                already_covered_by_recall=False,
                authorizer_statement="",
                direct_confirmation=Confirmation.NO_RECOLLECTION,
                call_duration_seconds=0,
                reachable=False,
                call_uuid=real_call_id,
                audio_sha256=transcript_hash,
            )
        return CallResult(
            already_covered_by_recall=bool(structured.get("already_covered_by_recall", False)),
            authorizer_statement=structured.get("authorizer_statement", ""),
            direct_confirmation=Confirmation(structured.get("direct_confirmation", "unclear")),
            call_duration_seconds=self.config.max_call_duration_seconds,
            secondary_authorizer_mentioned=structured.get("secondary_authorizer_mentioned"),
            secondary_claim_text=structured.get("secondary_claim_text"),
            reachable=True,
            call_uuid=real_call_id,
            audio_sha256=transcript_hash,
        )

    def _live_call(self, claim: Claim, phone_number: str) -> CallResult:  # pragma: no cover
        real_call_id = self.start_live_call(claim, phone_number)
        client = self._require_live_client()
        call = client.calls.wait_for_result(real_call_id)
        return self.parse_call_result(call)
