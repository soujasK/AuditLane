#!/usr/bin/env python3
"""
CLI entry point. Two ways to feed it a PR:

    # 1. Directly
    python scripts/run_verification.py --title "..." --body "..." --pr-ref "local#1"

    # 2. From a GitHub Actions pull_request event payload
    python scripts/run_verification.py --github-event $GITHUB_EVENT_PATH

Exit codes (meant to gate a CI job):
    0 = VERIFIED
    1 = BLOCKED           (a claimed authorization was contradicted)
    2 = NEEDS_HUMAN_REVIEW (fail closed — could not confidently verify)

The phonebook (name -> real phone number) is intentionally never derived
from the PR itself — see docs/SAFETY.md on why that would defeat the
whole point. It comes from a separately maintained JSON file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auditlane.calle_client import _CALL_BUDGET_FILE, build_recipient, build_task_prompt  # noqa: E402
from auditlane.claim_extractor import extract_claims_from_pr  # noqa: E402
from auditlane.config import Config  # noqa: E402
from auditlane.github_integration import post_pr_comment, set_commit_status  # noqa: E402
from auditlane.models import Verdict  # noqa: E402
from auditlane.verifier import AuditLaneVerifier  # noqa: E402

_EXIT_CODE = {
    Verdict.VERIFIED: 0,
    Verdict.BLOCKED: 1,
    Verdict.NEEDS_HUMAN_REVIEW: 2,
}


def _load_phonebook(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open() as f:
        raw = json.load(f)
    return {k.strip().lower(): v for k, v in raw.items()}


def _load_from_github_event(event_path: str):
    with open(event_path) as f:
        event = json.load(f)
    pr = event.get("pull_request", {})
    title = pr.get("title", "")
    body = pr.get("body", "") or ""
    number = pr.get("number")
    sha = pr.get("head", {}).get("sha")
    repo_full_name = event.get("repository", {}).get("full_name", "")
    return title, body, number, sha, repo_full_name


def _print_dry_run(config: Config, phonebook: dict, pr_ref: str, title: str, body: str) -> int:
    """Preview exactly what a live run would do — no call, live or mock,
    is ever placed. See --dry-run."""
    placed = 0
    if _CALL_BUDGET_FILE.exists():
        try:
            placed = json.loads(_CALL_BUDGET_FILE.read_text(encoding="utf-8")).get("live_calls_placed", 0)
        except Exception:
            pass

    print("=" * 72)
    print(" DRY RUN — nothing below was sent to CALL-E. No call, no cost.")
    print("=" * 72)
    print(f" dress_rehearsal : {config.dress_rehearsal}"
          f"  ({'would use mock fixtures' if config.dress_rehearsal else 'would place a REAL call'})")
    print(f" local call budget: {placed}/{config.max_live_calls} live calls already placed")
    print("-" * 72)

    claims = extract_claims_from_pr(title, body)
    if not claims:
        print(" No claims of undocumented verbal authorization found in this PR body.")
        print(" Nothing would be called.")
        return 0

    claim = claims[0]
    phone = phonebook.get(claim.authorizer_name.strip().lower())
    print(f" Authorizer   : {claim.authorizer_name}")
    print(f" Phone on file: {phone or '(none — would fail closed to NEEDS_HUMAN_REVIEW)'}")
    if phone:
        recipient = build_recipient(phone)
        print(f" Recipient    : {recipient}")
    print("-" * 72)
    print(" Task prompt that would be sent:")
    print(build_task_prompt(claim, max_call_seconds=config.max_call_duration_seconds))
    print("=" * 72)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AuditLane against one PR.")
    parser.add_argument("--title", default="")
    parser.add_argument("--body", default="")
    parser.add_argument("--pr-ref", default="local")
    parser.add_argument("--pr-number", type=int, default=None)
    parser.add_argument("--commit-sha", default=None)
    parser.add_argument("--github-event", default=None, help="Path to a GitHub Actions event JSON file")
    parser.add_argument(
        "--phonebook",
        default="phonebook.json",
        help="JSON file mapping authorizer name -> E.164 phone number",
    )
    parser.add_argument(
        "--post-to-github",
        action="store_true",
        help="Post the verdict as a PR comment / commit status (requires GITHUB_TOKEN)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Show exactly what would be sent to CALL-E (prompt, recipient, "
            "region/locale, current call budget usage) without placing any "
            "call, live or mock. Zero cost, zero API calls."
        ),
    )
    args = parser.parse_args()

    title, body, pr_number, commit_sha = args.title, args.body, args.pr_number, args.commit_sha

    # --github-event may be an explicit CLI path (local/manual runs), but
    # when this runs as a Docker GitHub Action, ${{ github.event_path }}
    # evaluated in the calling workflow is a HOST filesystem path that
    # doesn't exist inside this container -- Docker remaps that directory
    # to a different mount point. GITHUB_EVENT_PATH in this process's own
    # environment is the one GitHub already correctly rewrites for
    # whatever container is reading it, so prefer that when no explicit
    # path was given.
    github_event_path = args.github_event or os.environ.get("GITHUB_EVENT_PATH")
    if github_event_path:
        title, body, gh_number, gh_sha, _repo = _load_from_github_event(github_event_path)
        pr_number = pr_number or gh_number
        commit_sha = commit_sha or gh_sha

    config = Config.from_env()
    phonebook = _load_phonebook(args.phonebook)

    if args.dry_run:
        return _print_dry_run(config, phonebook, args.pr_ref, title, body)

    auditor = AuditLaneVerifier(config=config, phonebook=phonebook)

    outcome = auditor.audit_pr(pr_reference=args.pr_ref, title=title, body=body)

    print(outcome.to_markdown())
    print(f"[auditlane] dress_rehearsal={config.dress_rehearsal} verdict={outcome.verdict.value}")

    if args.post_to_github:
        # The verification itself already succeeded by this point — the
        # verdict above is real and correct. A GitHub API hiccup (bad
        # token, rate limit, network blip) posting THAT verdict back
        # must not turn into an unhandled traceback that replaces a
        # precise exit code (0/1/2) with Python's generic "crashed"
        # exit 1 — CI would then read a VERIFIED PR as if it had been
        # BLOCKED, or lose the distinction between BLOCKED and
        # NEEDS_HUMAN_REVIEW entirely. Report the failure loudly, but
        # still exit on the real verdict computed above.
        try:
            if pr_number:
                post_pr_comment(config, pr_number, outcome)
            if commit_sha:
                set_commit_status(config, commit_sha, outcome)
        except Exception as e:
            print(f"[auditlane] WARNING: verdict was {outcome.verdict.value}, but posting it back "
                  f"to GitHub failed ({e}). Exiting with the real verdict's code regardless.",
                  file=sys.stderr)

    return _EXIT_CODE[outcome.verdict]


if __name__ == "__main__":
    raise SystemExit(main())
