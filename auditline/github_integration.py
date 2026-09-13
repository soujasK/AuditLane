"""
Thin wrapper around GitHub's REST API — just enough to post the
verification verdict as a PR comment and set a commit status. Uses only
`requests` (already a dependency) so no GitHub SDK is required.

Nothing in here is called unless GITHUB_TOKEN and GITHUB_REPOSITORY are
set (see config.py) — running the verifier without them (e.g. the dress
rehearsal demo) simply skips posting anything back to GitHub.
"""

from __future__ import annotations

from typing import Optional

import requests

from .config import Config
from .models import Verdict, VerificationOutcome

_STATUS_STATE = {
    Verdict.VERIFIED: "success",
    Verdict.BLOCKED: "failure",
    Verdict.NEEDS_HUMAN_REVIEW: "pending",
}

_STATUS_DESCRIPTION = {
    Verdict.VERIFIED: "AuditLine: claim verified by phone",
    Verdict.BLOCKED: "AuditLine: claim contradicted, merge blocked",
    Verdict.NEEDS_HUMAN_REVIEW: "AuditLine: could not verify, human review required",
}


def post_pr_comment(config: Config, pr_number: int, outcome: VerificationOutcome) -> Optional[dict]:
    if not (config.github_token and config.github_repo):
        return None
    url = f"https://api.github.com/repos/{config.github_repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {config.github_token}",
        "Accept": "application/vnd.github+json",
    }
    body = {"body": outcome.to_markdown()}
    response = requests.post(url, headers=headers, json=body, timeout=15)
    response.raise_for_status()
    return response.json()


def set_commit_status(config: Config, commit_sha: str, outcome: VerificationOutcome) -> Optional[dict]:
    if not (config.github_token and config.github_repo):
        return None
    url = f"https://api.github.com/repos/{config.github_repo}/statuses/{commit_sha}"
    headers = {
        "Authorization": f"Bearer {config.github_token}",
        "Accept": "application/vnd.github+json",
    }
    body = {
        "state": _STATUS_STATE[outcome.verdict],
        "description": _STATUS_DESCRIPTION[outcome.verdict],
        "context": "auditline/verbal-authorization-check",
    }
    response = requests.post(url, headers=headers, json=body, timeout=15)
    response.raise_for_status()
    return response.json()
