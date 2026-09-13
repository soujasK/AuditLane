from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SUDO_SCRIPT = ROOT_DIR / "scripts" / "telephony_sudo.py"


def test_telephony_sudo_blocks_denied_authorizer():
    cmd = [
        sys.executable,
        str(SUDO_SCRIPT),
        "--authorizer",
        "@sarah_dba",
        "--reason",
        "Drop table",
        sys.executable,
        "-c",
        "print('CANARY_OUTPUT_SHOULD_NEVER_RUN')",
    ]
    import os
    env = dict(os.environ)
    env["AUDITLINE_DRESS_REHEARSAL"] = "true"
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert proc.returncode == 1
    assert "ACCESS DENIED" in proc.stderr
    # The string will be in the Target Command header line, but not as the final executed output
    assert proc.stdout.rstrip().endswith("------------------------------------------------------------------------")
    assert not proc.stdout.rstrip().endswith("'CANARY_OUTPUT_SHOULD_NEVER_RUN'")


def test_telephony_sudo_permits_confirmed_authorizer():
    cmd = [
        sys.executable,
        str(SUDO_SCRIPT),
        "--authorizer",
        "The architect",
        "--reason",
        "Change pattern",
        sys.executable,
        "-c",
        "print('EXECUTED_SUCCESS')",
    ]
    import os
    env = dict(os.environ)
    env["AUDITLINE_DRESS_REHEARSAL"] = "true"
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "AUTHORIZATION GRANTED" in proc.stdout
    assert "EXECUTED_SUCCESS" in proc.stdout
