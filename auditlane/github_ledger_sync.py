"""
Pulls audit_pr results into the same dashboard the telephony-gate hook
and Voice Sandbox already write to.

Why this exists as a separate poller instead of audit_pr just calling
append_ledger() directly: audit_pr runs inside the GitHub Actions
workflow, on GitHub's own remote runners -- a completely different
machine from wherever the dashboard is running. There is no shared
filesystem for it to append a ledger entry to; the PR comment it posts
IS its only output. So instead of writing locally, the dashboard reads
back out of GitHub -- turning the PR comment it already posts into a
ledger entry after the fact, client-side, from data already public on
the PR itself. No new write path, no new secret exposure.

Read-only against the GitHub REST API using GITHUB_TOKEN +
AUDITLANE_WATCH_REPOS (comma-separated "owner/repo" list) from
Config/env. If neither is configured, returns an empty list --
the local ledger (hook + Voice Sandbox) still renders on its own.
"""

from __future__ import annotations

import re
from typing import List, Optional

import requests

_VERDICT_RE = re.compile(r"###\s*Audit(?:Line|Lane)\s+verdict:\s*`(\w+)`", re.IGNORECASE)
_HOP_RE = re.compile(r"\*\*Hop\s+(\d+)\s*—\s*(.+?)\*\*\n((?:- .+\n?)*)")
_CLAIM_RE = re.compile(r'- Claim: "(.*)"')
_REACHED_RE = re.compile(r"- Reached: (\w+)")
_STATEMENT_RE = re.compile(r'- Their statement: "(.*)"')
_CONFIRMATION_RE = re.compile(r"- Confirmation: (\w+)")
_ENTAILMENT_RE = re.compile(
    r"- Entailment: (\w+) \(confidence ([\d.]+), engine: (.+?)\)"
)


def _parse_comment(body: str) -> Optional[dict]:
    """Turns one AuditLane verdict comment's markdown back into the
    structured fields a ledger entry needs. Returns None if this
    comment isn't one of ours (most repo comments won't be)."""
    verdict_match = _VERDICT_RE.search(body)
    if not verdict_match:
        return None
    verdict = verdict_match.group(1).upper()

    # Reason = the text between the verdict line and the first hop
    # block (or end of comment if there are no hops, e.g. "no claims
    # found").
    after_header = body[verdict_match.end():]
    first_hop_pos = after_header.find("**Hop")
    reason_block = after_header if first_hop_pos == -1 else after_header[:first_hop_pos]
    reason = reason_block.strip()

    hops = []
    for m in _HOP_RE.finditer(body):
        hop_index, authorizer, block = m.group(1), m.group(2), m.group(3)
        claim_m = _CLAIM_RE.search(block)
        reached_m = _REACHED_RE.search(block)
        statement_m = _STATEMENT_RE.search(block)
        confirmation_m = _CONFIRMATION_RE.search(block)
        entailment_m = _ENTAILMENT_RE.search(block)
        hops.append({
            "hopIndex": int(hop_index),
            "authorizer": authorizer,
            "role": "audit_pr Contact",
            "phone": "n/a (posted via GitHub Action)",
            "reached": (reached_m.group(1) == "True") if reached_m else False,
            "durationSec": 0,
            "claimText": claim_m.group(1) if claim_m else "",
            "statement": statement_m.group(1) if statement_m else "",
            "confirmation": confirmation_m.group(1) if confirmation_m else "unclear",
            "entailmentResult": entailment_m.group(1) if entailment_m else "n/a",
            "confidence": entailment_m.group(2) if entailment_m else "n/a",
            "engine": entailment_m.group(3) if entailment_m else "n/a",
            "callUuid": None,
            "audioSha256": None,
        })

    return {"verdict": verdict, "reason": reason, "hops": hops}


def fetch_github_audit_entries(github_token: str, repos: List[str]) -> List[dict]:
    """Polls each "owner/repo" in `repos` for recent issue/PR comments,
    keeps the ones that are real AuditLane verdicts, and returns them
    already shaped as ledger entries -- same shape build_gate_entry()
    produces, so the frontend renders both identically. Best-effort:
    any single repo or comment that fails to fetch/parse is skipped
    rather than failing the whole dashboard load."""
    if not github_token or not repos:
        return []

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    entries: List[dict] = []

    for repo in repos:
        repo = repo.strip()
        if not repo:
            continue
        try:
            resp = requests.get(
                f"https://api.github.com/repos/{repo}/issues/comments",
                headers=headers,
                params={"sort": "created", "direction": "desc", "per_page": 30},
                timeout=10,
            )
            resp.raise_for_status()
            comments = resp.json()
        except Exception:
            continue

        for comment in comments:
            parsed = _parse_comment(comment.get("body", ""))
            if not parsed:
                continue

            issue_url = comment.get("issue_url", "")
            pr_number = issue_url.rstrip("/").split("/")[-1] if issue_url else "?"
            pr_title = f"PR #{pr_number}"
            try:
                pr_resp = requests.get(issue_url, headers=headers, timeout=10)
                if pr_resp.ok:
                    pr_title = pr_resp.json().get("title", pr_title)
            except Exception:
                pass

            hops = parsed["hops"]
            first_authorizer = hops[0]["authorizer"] if hops else "n/a"
            entries.append({
                "id": "ghpr_" + str(comment.get("id", pr_number)),
                "prRef": f"{repo}#{pr_number}",
                "title": pr_title,
                "body": hops[0]["claimText"] if hops else parsed["reason"],
                "commitSha": str(comment.get("id", ""))[:10],
                "authorizer": first_authorizer,
                "timestamp": comment.get("created_at", "Just now"),
                "verdict": parsed["verdict"],
                "reason": parsed["reason"],
                "policy": "audit_pr — GitHub Actions Workflow",
                "engine": "heuristic-v1" if hops else "n/a",
                "hops": hops,
                "source": "github_action",
                "url": comment.get("html_url"),
            })

    return entries
