# Rubric mapping

For judges skimming quickly — where each judging criterion is addressed.

## Real World Impact

Autonomous coding agents fabricating claims about real-world state is a
documented, recent failure category (a Replit agent deleted a production
database and falsely claimed the deletion was unrecoverable; an AWS
engineer's coding agent resolved a production issue without required
peer approval). AuditLine targets a specific, narrow slice of that
problem — claims of *verbal, undocumented* human authorization — that
has no existing digital-artifact check, because none exists to check
against.

## Quality of the Idea

Every comparable tool we could find (approval gates, diff-review bots,
"turn-end checks" that compare an agent's claims to its own tool-call
logs) verifies against a digital record. None of them place a phone
call. This is deliberately the one category of claim where a digital
record can't exist by definition, which is what makes telephony (not
another dashboard) the right tool. See README "Why this, and not
something else."

## Technical Implementation

- CALL-E's `create_and_wait` is called with a purpose-built task prompt
  implementing an explicit interview methodology (open recall before
  the specific claim is read back — see `calle_client.build_task_prompt`).
- Multi-hop chains are followed for real: a confirmed hop that itself
  references a second authorizer triggers a second live call, up to a
  configurable limit (`auditline/verifier.py`).
- The entailment engine is a genuine, separate decision component (not
  another LLM call) with real logic, tested behavior, and a documented
  upgrade path to a pretrained NLI model.
- 21 tests, all passing, covering extraction edge cases (sentence-initial
  false positives, markdown line-wrap handling, deduplication),
  entailment behavior (contradiction, entailment, hedging, no overlap),
  and full orchestration (denial, confirmation, unreachable, multi-hop
  success, multi-hop exhaustion).
- The whole pipeline runs and is fully testable with zero external API
  access — see `demo/dress_rehearsal.py`.

## Product Experience & Demo

`python demo/dress_rehearsal.py` runs three complete scenarios
(blocked, verified via a two-hop chain, deferred to human review) in
under a second, with no setup beyond `pip install -r requirements.txt`.
The GitHub Action (`.github/workflows/auditline.yml`) shows the
real integration point: every PR gets a verdict as a comment and a
commit status, gating the merge without requiring any custom UI.
