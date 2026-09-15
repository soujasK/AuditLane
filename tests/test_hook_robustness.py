"""
Robustness tests for hooks/pretooluse_telephony_gate.py's stdin
handling. This isn't testing whether it makes the right allow/deny
call (that's danger_patterns.py's job, covered in
test_danger_patterns.py) — it's testing that malformed, missing, or
unexpected-shaped input can NEVER crash the hook.

That distinction matters more here than it would in most scripts: a
crash means a non-zero exit with a traceback instead of valid JSON on
stdout, and this project has no way to be certain that ambiguous
outcome is treated as "deny" by whatever's on the other end of the
hook rather than "allow". Every case below must exit 0 with valid,
parseable JSON — found via an actual stress test that caught two real
crashes (list-shaped payload, non-string command) before this file
existed.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "pretooluse_telephony_gate.py"


def _isolated_env(tmp_path: Path) -> dict:
    """Every subprocess invocation of the hook below must be isolated
    from two pieces of real, ambient state:

    1. AUDITLANE_DRESS_REHEARSAL — if the developer's own .env happens
       to have this off (true while iterating on a live demo, as it was
       for real during this project's own development), a subprocess
       that inherits the ambient environment and matches a danger
       pattern would place an ACTUAL phone call as a side effect of
       running the test suite. Forced true here regardless of ambient
       config — these tests exist to check crash-resistance, not to
       exercise live calling, so there's no reason they should ever be
       able to place one.
    2. AUDITLANE_LEDGER_PATH — without this, every subprocess run here
       appends to the real project .auditlane_ledger.json (see
       auditlane/ledger.py), polluting it with dozens of synthetic
       "rm -rf /data" / "DROP TABLE users" entries on every test run.
       Redirected to a per-test tmp file instead.
    3. AUDITLANE_CALL_BUDGET_PATH — same reasoning as #2, for
       auditlane/calle_client.py's call-budget guard. Not currently
       reachable in these tests (dress rehearsal never touches it), but
       isolated anyway so it can never silently start mattering later.
    """
    env = dict(os.environ)
    env["AUDITLANE_DRESS_REHEARSAL"] = "true"
    env["AUDITLANE_LEDGER_PATH"] = str(tmp_path / "test_ledger.json")
    env["AUDITLANE_CALL_BUDGET_PATH"] = str(tmp_path / "test_call_budget.json")
    return env

CASES = [
    ("empty_stdin", ""),
    ("malformed_json", "not json at all {{{"),
    ("missing_tool_name", json.dumps({"tool_input": {"command": "rm -rf /"}})),
    ("missing_tool_input", json.dumps({"tool_name": "Bash"})),
    ("non_bash_tool_dangerous_elsewhere", json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": "x.sh", "content": "rm -rf /"}})),
    ("command_is_null", json.dumps({"tool_name": "Bash", "tool_input": {"command": None}})),
    ("command_is_empty_string", json.dumps({"tool_name": "Bash", "tool_input": {"command": ""}})),
    ("tool_input_is_null", json.dumps({"tool_name": "Bash", "tool_input": None})),
    ("top_level_is_a_list", json.dumps(["not", "an", "object"])),
    ("top_level_is_a_string", json.dumps("just a string")),
    ("very_long_safe_command", json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "echo " + ("a" * 50000)}})),
    ("very_long_command_late_danger_match", json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": ("echo " + "a" * 50000) + " && rm -rf /data"}})),
    ("unicode_in_command", json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "echo 'héllo wörld 你好'"}})),
    ("embedded_newlines_heredoc", json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "cat <<'EOF'\nsome text\nDROP TABLE users;\nEOF"}})),
    ("command_is_an_int", json.dumps({"tool_name": "Bash", "tool_input": {"command": 12345}})),
    ("command_is_a_list", json.dumps({"tool_name": "Bash", "tool_input": {"command": ["rm", "-rf", "/"]}})),
]


@pytest.mark.parametrize("name,stdin_data", CASES, ids=[c[0] for c in CASES])
def test_hook_never_crashes(name, stdin_data, tmp_path):
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=15,
        env=_isolated_env(tmp_path),
    )
    assert result.returncode == 0, (
        f"hook exited {result.returncode} instead of 0 for case {name!r} — "
        f"stderr: {result.stderr}"
    )
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"hook did not emit valid JSON for case {name!r} — stdout: {result.stdout!r}")

    decision = parsed.get("hookSpecificOutput", {}).get("permissionDecision")
    assert decision in ("allow", "deny", "ask"), (
        f"case {name!r} produced an unrecognized permissionDecision: {decision!r}"
    )


def test_hook_denies_when_authorizer_not_configured(monkeypatch, tmp_path):
    monkeypatch.delenv("AUDITLANE_HOOK_AUTHORIZER", raising=False)
    env = _isolated_env(tmp_path)
    env.pop("AUDITLANE_HOOK_AUTHORIZER", None)
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "rm -rf /data"}}),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    parsed = json.loads(result.stdout)
    assert parsed["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_hook_allows_safe_command_with_no_config_needed(monkeypatch, tmp_path):
    """A safe command must pass through even with zero configuration —
    the gate should never require setup just to stay out of the way."""
    monkeypatch.delenv("AUDITLANE_HOOK_AUTHORIZER", raising=False)
    env = _isolated_env(tmp_path)
    env.pop("AUDITLANE_HOOK_AUTHORIZER", None)
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls -la"}}),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    parsed = json.loads(result.stdout)
    assert parsed["hookSpecificOutput"]["permissionDecision"] == "allow"
