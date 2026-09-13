---
name: auditline
description: >
  Before trusting an autonomous coding agent's claim that a human verbally
  authorized something (a schema drop, a breaking change, a production
  action) with no digital record of that approval, place a CALL-E call to
  the named person to independently verify it. Fails closed to human
  review on any denial, ambiguity, or unreachable contact.
---

# AuditLine skill

**Short description:** a merge-gate check for coding-agent PRs. Scans the
PR text for claims of undocumented verbal authorization ("confirmed with
X", "the architect verbally cleared this"), places a CALL-E call to the
named person using an open-recall-first interview method, compares their
statement against the claim, and returns `verified`, `blocked`, or
`needs_human_review`.

**Compatibility notes:** pure Python 3.11+, no framework dependency. Works
standalone via the CLI (`scripts/run_verification.py`) or wired into any
CI system that can run a Python step and read a PR's title/body — the
included GitHub Actions workflow is one example, not the only one.
Requires `calle-ai` (PyPI) only for live calls; the default dress-rehearsal
mode requires nothing beyond `requests` and `pytest`.

**Setup / install:**

```bash
pip install -r requirements.txt
cp phonebook.example.json phonebook.json   # replace with your real org directory
python demo/dress_rehearsal.py             # confirm it runs, zero API key needed
```

To go live: `pip install calle-ai`, set `CALLE_API_KEY`, set
`AUDITLINE_DRESS_REHEARSAL=false`. See `../../docs/SAFETY.md` first.

**Safety notes for real-world side effects:** places real phone calls to
real people when live. Dress rehearsal is the default and must be
explicitly disabled. The phonebook (name → phone number) is always
supplied separately and is never derived from the text being audited, so
a fabricated claim can't point the verification call at a number the
claim's author controls. Full detail in `../../docs/SAFETY.md`.

**Tests:** `python -m pytest ../../tests/ -v` — 21 tests, all offline, no
network access or API key required.

**Cancellation / rollback:** stateless per PR — there is no recurring job
to cancel. Removing the CI step (or the GitHub Actions workflow file)
stops all behavior immediately. A `blocked` or `needs_human_review`
verdict is only a commit status / PR comment; it carries no merge
authority of its own and can always be overridden by a human with normal
repository permissions.

**No secrets or personal data:** this skill directory contains no
credentials, no real phone numbers, and no real names — see
`phonebook.example.json` and the fixture bank in `../../auditline/calle_client.py`,
both fictional.
