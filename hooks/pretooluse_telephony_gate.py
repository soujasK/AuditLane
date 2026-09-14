#!/usr/bin/env python3
"""
Claude Code PreToolUse hook, matched to the Bash tool.

The problem this solves: a CLI wrapper a human or agent has to
deliberately invoke to gate one command only gates it if they choose to
run it through that wrapper — an honor system a careless or
hallucinating agent can simply skip. This hook sits in the harness's
own execution path instead, so it can't be skipped: every Bash command
an agent tries to run passes through here BEFORE it executes. Anything
matching danger_patterns.py is blocked until the configured authorizer
verbally confirms it over a real phone call; everything else passes
through untouched.

Fails closed on every error path (no authorizer configured, no phone on
file, the call is unreachable, CALL-E itself errors) — a broken or
misconfigured gate must never fail open into "run it anyway."

Registration (.claude/settings.json):
    {
      "hooks": {
        "PreToolUse": [{
          "matcher": "Bash",
          "hooks": [{
            "type": "command",
            "command": "python \"${CLAUDE_PROJECT_DIR}/hooks/pretooluse_telephony_gate.py\"",
            "timeout": 300
          }]
        }]
      }
    }

Configure which contact must approve dangerous commands via:
    AUDITLANE_HOOK_AUTHORIZER="the security lead"   # a phonebook.json key
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# auditlane.config calls load_dotenv() with no path, which searches from
# the current working directory upward — fine when this hook runs from
# inside its own project, but this hook is specifically meant to be
# registered from OTHER projects' .claude/settings.json too (that's the
# whole point of a portable gate). Loading .env explicitly from
# ROOT_DIR first means it's found correctly regardless of which
# project's directory Claude Code actually invokes this from.
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass

from auditlane.calle_client import CalleVerificationClient  # noqa: E402
from auditlane.config import Config  # noqa: E402
from auditlane.danger_patterns import check_command  # noqa: E402
from auditlane.ledger import append_ledger, build_gate_entry  # noqa: E402
from auditlane.models import Claim, Confirmation  # noqa: E402


def _log(match, authorizer: str, phone: Optional[str], verdict: str, reason: str, **kwargs) -> None:
    """Best-effort ledger write for a gate decision — this exists so the
    same real allow/deny events this hook already produces also show up
    in the web dashboard, not just on stdout back to Claude Code. Never
    allowed to affect the hook's actual decision: a ledger write failure
    here must not turn into a denied (or worse, allowed) command, so
    every call site already has its verdict decided before this runs,
    and any exception is swallowed after a stderr note."""
    try:
        append_ledger(build_gate_entry(
            command=kwargs.get("command", ""),
            authorizer=authorizer,
            phone=phone,
            verdict=verdict,
            reason=reason,
            pattern_name=match.pattern_name if match else "",
            pattern_description=match.description if match else "",
            **{k: v for k, v in kwargs.items() if k != "command"},
        ))
    except Exception as e:
        print(f"telephony-gate: warning — could not write ledger entry: {e}", file=sys.stderr)


def _load_phonebook() -> dict[str, str]:
    path = ROOT_DIR / "phonebook.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {k.strip().lower(): str(v) for k, v in data.items() if not k.startswith("_")}
    except Exception:
        return {}


def _allow(reason: str = "") -> dict:
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
    if reason:
        out["hookSpecificOutput"]["permissionDecisionReason"] = reason
    return out


def _deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # Can't even parse the hook input — fail closed rather than
        # silently passing an unexamined command through.
        print(json.dumps(_deny("telephony-gate: could not parse hook input; failing closed.")))
        return 0

    if not isinstance(payload, dict):
        # Valid JSON, but not the object shape we expect (e.g. a bare
        # list or string) — .get() below would crash on anything but a
        # dict, and a crash here must never look like "allow" to
        # whatever's on the other end of this hook.
        print(json.dumps(_deny(
            f"telephony-gate: hook input was valid JSON but not an object "
            f"(got {type(payload).__name__}); failing closed."
        )))
        return 0

    if payload.get("tool_name") != "Bash":
        print(json.dumps(_allow()))
        return 0

    tool_input = payload.get("tool_input")
    command = (tool_input or {}).get("command", "") if isinstance(tool_input, dict) else ""
    if not isinstance(command, str):
        # Seen in the wild during testing: a non-string command (e.g. an
        # int) crashes regex matching with a TypeError. Coerce rather
        # than trust — worst case a weird value gets checked as text
        # instead of silently skipping the check entirely.
        command = str(command) if command is not None else ""

    match = check_command(command)
    if not match:
        print(json.dumps(_allow()))
        return 0

    authorizer = os.environ.get("AUDITLANE_HOOK_AUTHORIZER", "").strip()
    if not authorizer:
        reason = (
            f"telephony-gate: command matches '{match.pattern_name}' ({match.description}) "
            f"but AUDITLANE_HOOK_AUTHORIZER is not set — no one to call. Set it to a "
            f"phonebook.json name and retry."
        )
        _log(match, "(unconfigured)", None, "NEEDS_HUMAN_REVIEW", reason, command=command,
             confirmation="unclear")
        print(json.dumps(_deny(reason)))
        return 0

    phonebook = _load_phonebook()
    phone = phonebook.get(authorizer.lower())
    if not phone:
        reason = (
            f"telephony-gate: command matches '{match.pattern_name}' ({match.description}) "
            f"but '{authorizer}' has no phone number on file in phonebook.json. Failing closed."
        )
        _log(match, authorizer, None, "NEEDS_HUMAN_REVIEW", reason, command=command,
             confirmation="unclear")
        print(json.dumps(_deny(reason)))
        return 0

    claim = Claim(
        authorizer_name=authorizer,
        claim_text=f"Authorize this command before it runs: '{command}'",
        subject=f"running a command that {match.description.lower()}: {command}",
        source_line=command,
    )

    try:
        base_cfg = Config.from_env()
        # Same "demo number -> forced mock" protection scripts/serve_ui.py
        # already applies to /api/test-call and /api/audit: a "555" number
        # is always a fixture, never a real destination, so treat it as
        # dress-rehearsal regardless of the global live/dress_rehearsal
        # setting. Without this, testing the gate with a fixture
        # authorizer while the project is configured live would try a
        # real call to an unroutable fake number instead of safely using
        # the mock fixture bank.
        call_cfg = base_cfg if "555" not in phone else Config(
            dress_rehearsal=True,
            calle_api_key=base_cfg.calle_api_key,
            calle_base_url=base_cfg.calle_base_url,
            entailment_confidence_threshold=base_cfg.entailment_confidence_threshold,
            max_hops=base_cfg.max_hops,
            max_call_duration_seconds=base_cfg.max_call_duration_seconds,
            max_live_calls=base_cfg.max_live_calls,
        )
        client = CalleVerificationClient(call_cfg)
        result = client.verify_claim(claim, phone)
    except Exception as e:
        reason = (
            f"telephony-gate: verification call to {authorizer} failed ({e}). Failing closed — "
            f"command NOT authorized."
        )
        _log(match, authorizer, phone, "NEEDS_HUMAN_REVIEW", reason, command=command,
             confirmation="unclear")
        print(json.dumps(_deny(reason)))
        return 0

    if not result.reachable:
        reason = (
            f"telephony-gate: could not reach {authorizer} to authorize this command "
            f"({match.description}). Failing closed."
        )
        _log(match, authorizer, phone, "NEEDS_HUMAN_REVIEW", reason, command=command,
             reached=False, confirmation="unclear",
             call_uuid=getattr(result, "call_uuid", None))
        print(json.dumps(_deny(reason)))
        return 0

    if result.direct_confirmation == Confirmation.CONFIRMED:
        reason = f"telephony-gate: {authorizer} verbally confirmed — \"{result.authorizer_statement}\""
        _log(match, authorizer, phone, "VERIFIED", reason, command=command,
             reached=True, duration_sec=getattr(result, "call_duration_seconds", 0) or 0,
             statement=result.authorizer_statement or "",
             confirmation=result.direct_confirmation.value,
             call_uuid=getattr(result, "call_uuid", None),
             audio_sha256=getattr(result, "audio_sha256", None))
        print(json.dumps(_allow(reason)))
        return 0

    reason = (
        f"telephony-gate: {authorizer} did not confirm (status: "
        f"{result.direct_confirmation.value}) — \"{result.authorizer_statement}\". Command blocked."
    )
    _log(match, authorizer, phone, "BLOCKED", reason, command=command,
         reached=True, duration_sec=getattr(result, "call_duration_seconds", 0) or 0,
         statement=result.authorizer_statement or "",
         confirmation=result.direct_confirmation.value,
         call_uuid=getattr(result, "call_uuid", None),
         audio_sha256=getattr(result, "audio_sha256", None))
    print(json.dumps(_deny(reason)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        # Final backstop. Every code path above already fails closed on
        # its own, but this exists so that even a bug I haven't found
        # yet can't turn into an unhandled traceback and a non-zero exit
        # with no JSON on stdout — an ambiguous outcome this gate can
        # never risk being read as "allow" by whatever's on the other
        # end of it.
        print(json.dumps(_deny(f"telephony-gate: internal error ({e}); failing closed.")))
        raise SystemExit(0)
