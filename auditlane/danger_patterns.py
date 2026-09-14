"""
Pattern-matching for commands dangerous enough to gate behind a real,
live verbal authorization call before they're allowed to run.

Deliberately simple and explicit (regex, not a model) for the same
reason claim_extractor.py is rule-based: it must be auditable, and it
must work with zero external dependencies so the gate itself can never
be the thing that fails.

This is intentionally conservative — false positives (gating something
that turns out to be harmless) cost a phone call; false negatives (a
truly dangerous command slipping through ungated) are the failure mode
that actually matters. When in doubt, match.

Coverage is grouped by category so a reviewer can see at a glance what
is and isn't covered, and so adding a new category doesn't mean hunting
through an undifferentiated list. See tests/test_danger_patterns.py for
the full positive/negative test matrix this is verified against.
"""

from __future__ import annotations

import re
from typing import NamedTuple, Optional


class DangerMatch(NamedTuple):
    pattern_name: str
    description: str


# (name, description, compiled regex) — description is shown to the
# authorizer/logged, so keep it a plain-English summary of the risk.
_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    # -- Databases ---------------------------------------------------
    ("sql_drop", "Drops a database table, database, or schema",
     re.compile(r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", re.IGNORECASE)),
    ("sql_drop_user", "Drops a database user or role",
     re.compile(r"\bDROP\s+(USER|ROLE)\b", re.IGNORECASE)),
    ("sql_truncate", "Truncates/deletes all rows from a table",
     re.compile(r"\bTRUNCATE\s+TABLE\b|\bDELETE\s+FROM\s+\w+\s*(;|$)", re.IGNORECASE)),
    ("sql_update_unscoped", "Mass-updates a table with no WHERE clause to scope it",
     re.compile(r"\bUPDATE\s+\w+\s+SET\b(?:(?!\bWHERE\b).)*(;|$)", re.IGNORECASE)),
    ("redis_flush", "Wipes an entire Redis database",
     re.compile(r"\bFLUSHALL\b|\bFLUSHDB\b", re.IGNORECASE)),
    ("crontab_remove", "Removes all of a user's scheduled cron jobs",
     re.compile(r"\bcrontab\s+-r\b")),

    # -- Filesystem ---------------------------------------------------
    ("rm_rf", "Recursively force-deletes files/directories",
     re.compile(r"\brm\s+(-\w*r\w*f\w*|-\w*f\w*r\w*|--recursive\s+--force|--force\s+--recursive)\b")),
    ("chmod_insecure", "Grants world-writable/insecure permissions recursively",
     re.compile(r"\bchmod\s+(-R\s+)?0?777\b")),
    ("disk_format", "Formats/overwrites a disk or partition",
     re.compile(r"\bmkfs(\.\w+)?\b|\bdd\s+.*of=/dev/")),

    # -- Remote code execution ----------------------------------------
    ("curl_pipe_shell", "Pipes a remote download straight into a shell interpreter",
     re.compile(r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(bash|sh|zsh)\b")),

    # -- Infrastructure / orchestration ---------------------------------
    ("terraform_destroy", "Destroys provisioned infrastructure",
     re.compile(r"\bterraform\s+destroy\b")),
    ("kubectl_delete", "Deletes a Kubernetes resource",
     re.compile(r"\bkubectl\s+delete\b")),
    ("docker_system_prune", "Removes all unused Docker data",
     re.compile(r"\bdocker\s+system\s+prune\b.*(-a|--all)\b")),
    ("cloud_delete", "Deletes a cloud resource (bucket, instance, role, project)",
     re.compile(r"\baws\s+\S+\s+delete-\S+\b|\bgcloud\s+\S+\s+delete\b|\baz\s+\S+\s+delete\b")),
    ("heroku_destroy", "Permanently destroys a Heroku app",
     re.compile(r"\bheroku\s+apps?:destroy\b")),

    # -- Version control ------------------------------------------------
    ("git_force_push", "Force-pushes, can overwrite remote history",
     re.compile(r"\bgit\s+push\s+.*(--force\b|-f\b)")),
    ("git_reset_hard", "Discards local commits/changes irreversibly",
     re.compile(r"\bgit\s+reset\s+--hard\b")),
    ("git_branch_delete_force", "Force-deletes a git branch",
     re.compile(r"\bgit\s+branch\s+-D\b")),
    ("git_clean_force", "Irreversibly deletes untracked files",
     re.compile(r"\bgit\s+clean\s+.*-\w*[fF]\w*")),

    # -- System / network -----------------------------------------------
    ("system_shutdown", "Shuts down, reboots, or halts the machine",
     re.compile(r"\b(shutdown|reboot|halt|poweroff)\b(?!\s*-{1,2}help)")),
    ("kill_broad", "Kills every process (not a specific, scoped one)",
     re.compile(r"\bkill\s+-9\s+-1\b|\bkillall\b")),
    ("firewall_flush", "Flushes all firewall rules, opening the machine up",
     re.compile(r"\biptables\s+-F\b|\bufw\s+disable\b")),

    # -- Package publishing (irreversible once live) ---------------------
    ("package_publish", "Publishes a package to a public registry — hard to fully retract",
     re.compile(r"\bnpm\s+publish\b|\bpip\s+upload\b|\btwine\s+upload\b|\bcargo\s+publish\b")),
]


def check_command(command: str) -> Optional[DangerMatch]:
    """Returns the first matching danger pattern, or None if the command
    doesn't match anything on the list. Checks in the order defined
    above; a command can only ever match once here (first hit wins) —
    the caller doesn't need every match, just whether to gate at all."""
    if not command:
        return None
    for name, description, pattern in _PATTERNS:
        if pattern.search(command):
            return DangerMatch(pattern_name=name, description=description)
    return None
