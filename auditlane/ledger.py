"""
The real, durable, server-side verification ledger — every result from
any surface that places a call or makes a gate decision (the web
dashboard's Audit Pull Request / Voice Sandbox / telephony-sudo panels,
and the Claude Code telephony-gate hook) is appended here, so it durably
exists independent of any one browser tab or terminal session.

Shared by scripts/serve_ui.py (the dashboard's read/write surface) and
hooks/pretooluse_telephony_gate.py (which has no HTTP server to write
through — it appends directly) so there's exactly one ledger format and
one place that can drift, not two copies that quietly diverge.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
# Overridable so tests (and anything else that shouldn't touch the real,
# committed-nowhere-but-still-shared project ledger) can redirect writes
# to an isolated tmp file instead. Without this, subprocess-invoked hook
# tests were silently appending to the real .auditlane_ledger.json on
# every test run — see tests/test_hook_robustness.py.
LEDGER_PATH = Path(os.environ["AUDITLANE_LEDGER_PATH"]) if os.environ.get("AUDITLANE_LEDGER_PATH") \
    else ROOT_DIR / ".auditlane_ledger.json"


def load_ledger() -> list[dict]:
    if LEDGER_PATH.exists():
        try:
            data = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def append_ledger(entry: dict) -> None:
    ledger = load_ledger()
    ledger.insert(0, entry)
    try:
        LEDGER_PATH.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Warning: could not persist ledger entry: {e}", file=sys.stderr)


def build_gate_entry(
    *,
    command: str,
    authorizer: str,
    phone: Optional[str],
    verdict: str,
    reason: str,
    reached: bool = False,
    duration_sec: int = 0,
    statement: str = "",
    confirmation: str = "unclear",
    call_uuid: Optional[str] = None,
    audio_sha256: Optional[str] = None,
    pattern_name: str = "",
    pattern_description: str = "",
) -> dict:
    """A telephony-gate decision, in the same shape the dashboard's own
    ledger entries already use, so both render through identical
    frontend code. Called for every gate decision, not just the ones
    that placed a real call — a command denied for "no authorizer
    configured" is still a real gate event worth a durable record."""
    entry_id = "gate_" + (call_uuid or _stable_id(command))
    return {
        "id": entry_id,
        "prRef": "telephony-gate#" + _stable_id(command)[:8],
        "title": f"telephony-gate: {command[:70]}",
        "body": command,
        "commitSha": (call_uuid or _stable_id(command)).replace("_", "")[:10],
        "authorizer": authorizer,
        "timestamp": "Just now",
        "verdict": verdict,
        "reason": reason,
        "policy": f"telephony-gate — Claude Code PreToolUse Hook"
                  + (f" ({pattern_name}: {pattern_description})" if pattern_name else ""),
        "engine": "n/a (raw call, no entailment)",
        "hops": [{
            "hopIndex": 0,
            "authorizer": authorizer,
            "role": "telephony-gate Contact",
            "phone": phone or "n/a",
            "reached": reached,
            "durationSec": duration_sec,
            "claimText": f"Authorize this command before it runs: '{command}'",
            "statement": statement,
            "confirmation": confirmation,
            "entailmentResult": "n/a",
            "confidence": "n/a",
            "engine": "n/a",
            "callUuid": call_uuid,
            "audioSha256": audio_sha256,
        }],
    }


def _stable_id(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
