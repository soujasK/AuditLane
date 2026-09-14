#!/usr/bin/env python3
"""
Run this to see the whole pipeline end to end with zero setup:

    python demo/dress_rehearsal.py

No CALLE_API_KEY, no network access, and no real phone calls are made —
CalleVerificationClient stays in dress-rehearsal mode and answers from
the fixture bank in auditlane/calle_client.py. This is exactly what
a judge should be able to run cold to see the project work.

It runs three scenarios back to back:
  1. A denied claim  -> BLOCKED
  2. A confirmed multi-hop chain -> VERIFIED (2 hops)
  3. An unlisted authorizer -> NEEDS_HUMAN_REVIEW (fail closed)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auditlane.config import Config  # noqa: E402
from auditlane.verifier import AuditLaneVerifier  # noqa: E402

PHONEBOOK = {
    "sarah": "+15550001111",
    "@sarah_dba": "+15550001111",
    "the architect": "+15550002222",
    "the security lead": "+15550003333",
}


def run_scenario(title: str, pr_title: str, pr_body: str) -> None:
    print("=" * 72)
    print(title)
    print("=" * 72)
    print(f"PR title: {pr_title}")
    print(f"PR body:  {pr_body}")
    print("-" * 72)

    config = Config(dress_rehearsal=True)
    auditor = AuditLaneVerifier(config=config, phonebook=PHONEBOOK)
    outcome = auditor.audit_pr(pr_reference="demo#1", title=pr_title, body=pr_body)

    print(outcome.to_markdown())
    print(f"FINAL VERDICT: {outcome.verdict.value.upper()}")
    print()


def main() -> None:
    sample_pr = Path(__file__).parent / "sample_pr_description.md"
    sample_body = sample_pr.read_text()

    run_scenario(
        "SCENARIO 1 — an agent claims Sarah cleared a drop; she didn't.",
        pr_title="Drop legacy v1_accounts table",
        pr_body="As confirmed with @sarah_dba during standup, this is safe to drop the legacy table.",
    )

    run_scenario(
        "SCENARIO 2 — a multi-hop chain that fully checks out.",
        pr_title="Change access pattern",
        pr_body=sample_body,
    )

    run_scenario(
        "SCENARIO 3 — nobody has this authorizer's number on file.",
        pr_title="Rotate the signing key",
        pr_body="Confirmed with Random Person that rotating the signing key today is fine.",
    )

    print("=" * 72)
    print("All three scenarios ran with zero API keys and zero real phone calls.")
    print("Switch AUDITLANE_DRESS_REHEARSAL=false + a real CALLE_API_KEY")
    print("to place real calls. Read docs/SAFETY.md first.")
    print("=" * 72)


if __name__ == "__main__":
    main()
