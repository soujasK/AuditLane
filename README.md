# AuditLine

**Before an autonomous coding agent's claim of human approval gets trusted, call the human it claims approved it — and check if their story matches.**

Built for [CALL-E: Your Code Is Calling](https://call-e.devpost.com/). Uses CALL-E's out-of-band phone-call capability to verify the one category of claim that has no digital record to check against by definition: undocumented, verbal authorization.

---

## The problem

Autonomous coding agents (Devin, SWE-agent, OpenHands, and friends) increasingly push commits and open PRs directly. Sometimes their commit messages or PR descriptions claim a human authorized something informally:

> "As confirmed with @sarah_dba during standup, this is safe to drop the legacy `v1_accounts` table across regional shards."

That claim might be true. It might also be a confabulation — agents have been documented fabricating claims about real-world state before, including a well-known case where a coding agent deleted a production database and then falsely claimed the deletion was unrecoverable when it wasn't.

Static linters and CI can't check this kind of claim. There is no ticket, no Slack message, no git blame for a hallway conversation — by definition, the only way to verify it is to ask the person.

## Why this can only be telephony

Every other category of "agent claim" (tests passed, a file was written, a commit has a SHA) has a digital artifact to check against. A *verbal, undocumented* claim of authorization has none — that's what makes it a hallway conversation instead of a ticket. A phone call to the named person is the only out-of-band channel that can check it.

## What it does

```
PR text
   │  (rule-based extraction, zero external calls — see auditline/claim_extractor.py)
   ▼
Claim("Sarah", "confirmed dropping v1_accounts is fine", ...)
   │  (CALL-E: client.calls.create_and_wait — see auditline/calle_client.py)
   ▼
CallResult(statement="No — we agreed to keep it...", direct_confirmation="denied")
   │  (entailment engine compares claim vs. statement — see auditline/entailment.py)
   ▼
HopResult(contradiction=True)
   │
   ▼
Verdict: BLOCKED — PR comment posted, merge gated
```

If the claim itself references a second person's approval ("I was told by the security lead it was fine"), AuditLine follows the chain — calling that person too, up to `AUDITLINE_MAX_HOPS` hops — before deciding.

**Decision policy is deliberately simple and fails closed:**
- Any hop the authorizer denies, or that scores as a confident contradiction → **BLOCKED**
- Every hop confirmed with confident agreement, chain fully resolved → **VERIFIED**
- Anything else — unreachable, no phone on file, hedge/low confidence, chain too long → **NEEDS_HUMAN_REVIEW**

It never auto-merges on ambiguity. Uncertainty always routes to a human, never to a guess.

### The interrogation method

The CALL-E prompt asks for **open, unprompted recall first** ("what did you discuss about the accounts table today?"), and only reads back the specific claim if the open answer doesn't already address it. Leading with "the agent says you approved this, right?" invites a reflexive yes — this is the same free-recall-before-recognition principle used in real witness-interview practice, and it's what actually catches a fabricated claim. See `calle_client.build_task_prompt()`.

## Where the ML is genuinely load-bearing

`auditline/entailment.py` implements the judgment call that decides BLOCKED vs. VERIFIED vs. defer-to-human — this isn't a bolted-on feature, it's the thing that makes the pipeline's output auditable and consistent rather than "another LLM call whose reasoning might drift."

- **`HeuristicEntailmentEngine`** (default): zero dependencies, zero downloads, fully offline — negation- and lexical-overlap-based. This is what tests, CI, and the dress-rehearsal demo use, on purpose, so the whole project is judgeable without any external API access.
- **`TransformerEntailmentEngine`** (optional): a pretrained NLI model (e.g. `roberta-large-mnli`) via `transformers`, for production-grade entailment quality. Requires `pip install transformers torch` and network access to download weights — not assumed available in every environment, so it's opt-in, not default. Swap it in by passing `entailment_engine=TransformerEntailmentEngine()` to `ChronoAuditor`.

CALL-E does the one thing nothing else can: get a real, unscripted, in-the-moment human account. The entailment engine does the one thing it's suited for: a consistent, explainable verdict on whether that account matches the claim.

## Quickstart — see it work in 10 seconds, no API key

```bash
pip install -r requirements.txt
python demo/dress_rehearsal.py
```

This runs three full scenarios (a denied claim, a resolved two-hop chain, an unreachable authorizer) entirely offline, using the fixture bank in `auditline/calle_client.py`. No `CALLE_API_KEY`, no network access, no real phone calls.

### Web UI — Verification Ledger Dashboard

Launch the local compliance ledger interface:

```bash
python scripts/serve_ui.py --port 8080
```

Then navigate to `http://localhost:8080` in your browser to inspect the audit ledger, multi-hop verification timelines, organization directory, and trigger interactive PR verifications.

Run the test suite:

```bash
python -m pytest tests/ -v
```

Run it against your own PR text from the command line:

```bash
cp phonebook.example.json phonebook.json   # edit with your real org directory
python scripts/run_verification.py --title "..." --body "..." --pr-ref "myrepo#123"
```

Exit codes are CI-gate-friendly: `0` = verified, `1` = blocked, `2` = needs human review.

### Going live

Live calls are **off by default** (`AUDITLINE_DRESS_REHEARSAL=true`). To place real calls:

```bash
pip install calle-ai
export AUDITLINE_DRESS_REHEARSAL=false
export CALLE_API_KEY=your_real_key
```

Read **[docs/SAFETY.md](docs/SAFETY.md)** first — this makes real phone calls to real colleagues.

### Wiring it into a repo

See `.github/workflows/auditline.yml` — it runs on every PR, posts the verdict as a comment, and sets a commit status. Dress rehearsal stays on until a repository variable and a secret are both explicitly set.

## Project layout

```
auditline/
  claim_extractor.py    Rule-based extraction of verbal-authorization claims
  calle_client.py        CALL-E task/schema builders + real SDK client + mock backend
  entailment.py           Heuristic (default) and optional transformer NLI engines
  verifier.py             Multi-hop orchestration + fail-closed decision policy
  github_integration.py   Post verdict as PR comment / commit status
  models.py, config.py    Data classes and environment-driven configuration
scripts/run_verification.py   CLI entry point (used by the GitHub Action)
demo/dress_rehearsal.py        Zero-setup, offline, three-scenario walkthrough
tests/                          21 unit/integration tests, all offline
docs/SAFETY.md                  Read before ever going live
docs/RUBRIC_MAPPING.md          How this maps to the hackathon's judging criteria
skills/auditline-skill/      Packaged as a reusable Agent Skill contribution
```

## Extension points (not built, deliberately out of scope for the hackathon window)

- **LLM-based claim extraction** for higher recall on messier phrasing than the current regex extractor handles (see the module docstring in `claim_extractor.py` for its known scope limits).
- **Fanning out multiple claims per PR** — the current version audits the first claim found per run to keep demo output readable; the data model (`extract_claims` returns a list) already supports auditing all of them.
- **A real org-directory integration** instead of a flat JSON phonebook file.

## Known limitations, stated plainly

- The rule-based extractor is tuned for common phrasings ("confirmed with X", "X verbally cleared", "the database admin approved") and will miss more creative phrasing — false negatives, not false positives, are the expected failure mode, which is the safer direction to err in.
- The heuristic entailment engine is a deliberately simple lexical-overlap approximation, not a claim of state-of-the-art NLI accuracy. It's designed to be conservative (defaults to "neutral" / defer-to-human when unsure) rather than confidently wrong.
- The phonebook must be maintained separately from the PR content — AuditLine never dials a number that appeared in the text it's auditing, on purpose (see SAFETY.md).

## Why this, and not something else

Everything else in this space that we could find — approval-gate tools, diff-review bots, turn-end checks that compare an agent's claims to its own tool-call logs — verifies against a *digital* artifact. None of them phone the person. AuditLine is built specifically for the claim category that was never going to have a digital trail in the first place.
