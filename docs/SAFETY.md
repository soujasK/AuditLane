# Safety notes

This project places real phone calls to real colleagues when it is not
in dress-rehearsal mode. Read this before flipping that switch.

## Dress rehearsal is the default, on purpose

`AUDITLANE_DRESS_REHEARSAL` defaults to `true`. Going live requires
**both** setting it to `false` **and** providing a real `CALLE_API_KEY` —
two explicit, deliberate actions. There is no code path that places a
real call by accident.

## What a live call actually does

- Discloses plainly, in the first turn, that it is an automated
  engineering change-control verification call, not a real security
  incident, if the person asks.
- Is capped at `AUDITLANE_MAX_CALL_SECONDS` (default 180s).
- Never argues with a denial — if the person says they didn't authorize
  something, the call ends. AuditLane does not try to talk anyone
  into confirming something they've denied.
- Never asks for or transmits real credentials, account numbers, or any
  secret. It only asks what the person recalls discussing.

## The phonebook is never derived from the PR

`AuditLaneVerifier` looks up phone numbers from a separately maintained
`phonebook.json`, never from names or numbers appearing in the PR text
itself. If it dialed whatever number appeared in the text being
audited, an attacker (or a fabricating agent) could point the "verification"
call at a number they control and have it self-confirm. The phonebook
must come from your own org directory, kept out of the repository
(`.gitignore` already excludes it — only `phonebook.example.json`, with
fixture data, is committed).

## No secrets or personal data in this repository

- `phonebook.example.json` contains fabricated example numbers only.
- `auditlane/calle_client.py`'s fixture bank (`default_mock_responses`)
  is fictional demo data — no real names, no real statements from real
  people.
- `.env.example` documents required variables but ships no real values.
- `.gitignore` excludes `.env` and `phonebook.json` so real credentials
  and a real org directory are never committed by accident.

## Rate limiting and avoiding a harassment feel

A local call-budget guard (`AUDITLANE_MAX_LIVE_CALLS`, default 3) caps
the total number of live calls placed per session, tracked on disk
independent of CALL-E's own account balance — see
`auditlane/calle_client.py`'s `_enforce_call_budget`. This bounds the
blast radius of a retry loop or a misconfiguration; it is a global cap,
not yet a true per-person rate limit (e.g. "no more than N calls to the
same specific authorizer per day" regardless of total volume) — that
finer-grained version is still a reasonable extension for a production
deployment fielding many distinct authorizers.

## Fail-closed is the whole safety model

Every uncertain outcome — unreachable person, no phone on file, a
hedge, an ambiguous statement, a chain of claims too long to fully
resolve — routes to `NEEDS_HUMAN_REVIEW`, never to a silent pass. The
only way to get a `VERIFIED` result is for every hop in the chain to be
both a clear "yes" from the person and a confident textual match to the
claim. See `auditlane/verifier.py` for the exact decision logic.

## Cancellation / rollback

This tool only ever gates a merge (via commit status) or comments on a
PR — it takes no other action, and reverses cleanly: removing the
GitHub Action workflow file stops all behavior immediately, and a
`BLOCKED` or `NEEDS_HUMAN_REVIEW` status can always be overridden by a
human with normal repository permissions. AuditLane has no merge
authority of its own.
