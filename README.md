# AuditLane

**Before an autonomous agent runs a dangerous command, or before its claim of human approval gets trusted, call the human — and check if their story actually matches.**

Built for [CALL-E: Your Code Is Calling](https://call-e.devpost.com/). Uses CALL-E's out-of-band phone-call capability for the one category of check nothing else can do: an undocumented, verbal, in-the-moment human account.

**Hackathon skill contribution (real, open, mergeable):** [CALLE-AI/awesome-phone-call-agents#700](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/700)

**What CALL-E is, briefly:** an API that lets a piece of software place a real outbound phone call to a real person and have a structured conversation with them, returning a transcript and a parsed result. AuditLane uses it as the one verification channel a digital-only system doesn't have — a live, unscripted, in-the-moment human account.

---

## Inspiration

Autonomous coding agents are getting real execution access now — shell commands, infrastructure changes, database access — through hooks, MCP servers, and CI pipelines. The standard mitigation is "the agent should ask a human before doing anything dangerous." That's an honor system: a careless, confused, or compromised agent just doesn't ask, and nothing stops it. There are documented, real cases of coding agents fabricating claims about real-world state to justify what they'd already done — a well-known one being an agent that deleted a production database and then falsely claimed the deletion was unrecoverable when it wasn't.

CALL-E's premise — give an agent a real phone — is the one tool that can actually close this gap. A verbal, in-the-moment human account is the one category of claim that has no digital record to check against by definition. That's what we built for.

## What it does

Two capabilities, one verification core, one fail-closed decision policy — full detail below, but in short: `telephony-gate` intercepts every dangerous `Bash` command a Claude Code agent tries to run, before execution, unconditionally, and blocks it until a real phone call to a configured human is explicitly confirmed. `audit_pr` runs as a GitHub Actions workflow on every pull request, scans the PR text for claims of undocumented verbal authorization, places a real call to the named person to check, and posts the verdict back as a PR comment and a commit status that gates the merge.

## How we built it

A Python engine (danger-pattern regex matching, a real CALL-E SDK client with region/locale-aware E.164 recipient building, multi-hop claim verification, a heuristic entailment engine with an optional transformer-NLI upgrade path) shared by two very different front doors: a Claude Code hook speaking stdin/stdout JSON, and a Docker GitHub Action. A web dashboard unifies both — which turned out to be the interesting engineering problem, since the hook writes results locally but the GitHub Action runs on GitHub's own remote runners with no shared filesystem. The dashboard polls the GitHub REST API for the Action's PR comments and parses them back into the same ledger shape the hook writes locally, so both capabilities render in one place.

## Challenges we ran into

Most of the real bugs only showed up by actually running things for real, not by reading the code:

- **Region/locale routing**: the original bug that started this project — calls to Indian numbers were silently failing because the recipient object never carried region/locale.
- **Two separate GitHub Actions bugs**, found by opening real test PRs and watching them fail: the `github.*` context doesn't resolve inside a Docker action's own `action.yml` when it's referenced cross-repo (`uses: owner/repo@ref`), only inside an actual workflow file — and separately, `${{ github.event_path }}` evaluates to a *host* filesystem path that Docker remaps to a different mount point inside the container.
- **A call-budget guard silently pointing at the wrong file**: the safety cap on real calls placed used a bare relative path, so when the hook ran from a different project's directory (its actual intended use case), it wrote its count into *that* project instead of tracking a real global total — meaning the cap was never actually enforced cross-project until we caught it.
- **Getting a well-behaved coding agent to actually trigger the thing being demoed**: a cautious agent that checks credentials, checks whether a target exists first, and asks for confirmation is good behavior in general — but it meant the hook, which only intercepts actual Bash tool calls, never got reached, because the agent's own reasoning stopped it first in chat.
- A stress-test suite built specifically to break the hook found two real crash bugs (a list-shaped payload, a non-string command field) before anyone else ever saw them.

## Accomplishments that we're proud of

Every claim in this project is backed by something that actually happened, not simulated: real live phone calls placed and answered, both the block and the confirm path, through both the hook and the GitHub Action, with real transcripts and real status checks gating a real PR. 127 tests, all offline, including a dedicated adversarial suite whose entire job is proving the hook cannot crash into an ambiguous, possibly-unsafe state no matter what garbage hits its stdin.

## What we learned

The gap between "the code looks correct" and "it's been proven against the real system" is where the actual bugs live — every meaningful bug this session was found by running something for real and watching it fail, not by re-reading the source. And an agent's own good judgment, however real, isn't a substitute for an enforcement point that doesn't depend on the agent choosing to cooperate.

## What's next for AuditLane

LLM-based claim extraction for higher recall on messier phrasing than the current regex extractor catches. Adapters for other agent hosts — the verification core has zero Claude Code coupling, so porting the enforcement point to another harness's equivalent interception mechanism is new adapter code, not a rewrite. A real org-directory integration instead of a flat phonebook file, and true per-authorizer rate limiting instead of a global session cap.

---

## Two capabilities, one verification core

**`telephony-gate`** — a Claude Code `PreToolUse` hook. Every `Bash` command an agent tries to run passes through it *before execution*, unconditionally — the agent has no code path that skips it. If the command matches a dangerous pattern (`DROP TABLE`, `rm -rf`, `terraform destroy`, `curl | bash`, force-push, and 18 others — see `auditlane/danger_patterns.py`), execution is blocked until a real, live phone call to a configured human is explicitly confirmed.

**`audit_pr`** — the original capability. Scans a PR's title/body for claims of undocumented verbal authorization ("confirmed with X", "the architect verbally cleared this"), places a call to the named person, compares their statement against the claim, and returns `verified`, `blocked`, or `needs_human_review`.

Both share the same engine (`auditlane/calle_client.py`, `auditlane/verifier.py`) and the same fail-closed decision policy — see below.

## The problem `telephony-gate` solves

The common mitigation for "agent about to do something dangerous" is "the agent should ask a human first." That's an honor system — a careless, confused, or compromised agent just doesn't ask, and nothing stops it. `telephony-gate`'s actual contribution isn't the phone call, it's *where the gate lives*: installed as a hook, it sits in the harness's own execution path instead of depending on the agent's cooperation.

## The problem `audit_pr` solves

Autonomous coding agents (Devin, SWE-agent, OpenHands, and friends) increasingly push commits and open PRs directly. Sometimes their commit messages or PR descriptions claim a human authorized something informally:

> "As confirmed with @sarah_dba during standup, this is safe to drop the legacy `v1_accounts` table across regional shards."

That claim might be true. It might also be a confabulation — agents have been documented fabricating claims about real-world state before, including a well-known case where a coding agent deleted a production database and then falsely claimed the deletion was unrecoverable when it wasn't. Static linters and CI can't check this kind of claim — there's no ticket, no Slack message, no git blame for a hallway conversation. By definition, the only way to verify it is to ask the person.

## What happens end to end

```
telephony-gate:
  Bash command --danger_patterns.py--> match?
     │                                    │
     │ no                                 │ yes
     ▼                                    ▼
   runs untouched              CALL-E calls the configured authorizer
                                          │  free-recall interview, then verdict
                                          ▼
                              allow (confirmed) / deny (denied, unreachable,
                              no config, no phone on file, internal error —
                              every one of these denies, never allows by default)

audit_pr:
  PR text --regex extraction--> Claim("Sarah", "confirmed dropping v1_accounts", ...)
     │
     ▼
  CALL-E calls Sarah --> CallResult(statement="No — we agreed to keep it...", denied)
     │
     ▼
  entailment engine compares claim vs. statement --> HopResult(contradiction=True)
     │
     ▼
  Verdict: BLOCKED — PR comment posted, merge gated
```

If a claim references a second person's approval ("I was told by the security lead it was fine"), `audit_pr` follows the chain — calling that person too, up to `AUDITLANE_MAX_HOPS` hops — before deciding.

**Decision policy, identical for both capabilities, deliberately simple and fails closed:**
- Denial, or a confident contradiction → **BLOCKED** / denied
- Confirmed with confident agreement (every hop, for `audit_pr`) → **VERIFIED** / allowed
- Anything else — unreachable, no phone on file, hedge/low confidence, chain too long, misconfigured, internal error → **NEEDS_HUMAN_REVIEW** / denied

It never proceeds on ambiguity. Uncertainty always routes to a human, never to a guess — verified with a dedicated crash-resistance test suite (`tests/test_hook_robustness.py`), not just claimed: malformed input, missing config, wrong types, unexpected shapes all deny cleanly, none of them crash into an ambiguous non-zero exit.

### The interrogation method

The CALL-E prompt asks for **open, unprompted recall first** ("what did you discuss about the accounts table today?" / "what did you approve regarding this command?"), and only reads back the specific claim if the open answer doesn't already address it. Leading with "the agent says you approved this, right?" invites a reflexive yes — this is the same free-recall-before-recognition principle used in real witness-interview practice, and it's what actually catches a fabricated claim. See `calle_client.build_task_prompt()`.

## Where the ML is genuinely load-bearing

`auditlane/entailment.py` implements the judgment call that decides BLOCKED vs. VERIFIED vs. defer-to-human for `audit_pr` — this isn't a bolted-on feature, it's the thing that makes the pipeline's output auditable and consistent rather than "another LLM call whose reasoning might drift."

- **`HeuristicEntailmentEngine`** (default): zero dependencies, zero downloads, fully offline — negation- and lexical-overlap-based. This is what tests, CI, and the dress-rehearsal demo use, on purpose, so the whole project is judgeable without any external API access.
- **`TransformerEntailmentEngine`** (optional): a pretrained NLI model (e.g. `roberta-large-mnli`) via `transformers`, for production-grade entailment quality. Requires `pip install transformers torch` and network access to download weights — not assumed available in every environment, so it's opt-in, not default. Swap it in by passing `entailment_engine=TransformerEntailmentEngine()` to `AuditLaneVerifier`.

`telephony-gate` doesn't need entailment scoring — it's a direct yes/no confirmation, not a claim-vs-statement comparison — but shares the same call/interview/fail-closed machinery.

## Why Claude Code specifically

Most comparable "agent skill" write-ups are platform-agnostic instruction patterns any capable agent could theoretically follow. `telephony-gate` is deliberately different: its entire value is that the gate is a *real interception point an agent cannot skip*, and that guarantee only exists because it's built against Claude Code's actual `PreToolUse` hook contract, not a documented convention. Something proven to work against one real, currently-widely-used agent's actual execution path — 129 tests, fired live during development, two real crash bugs found and fixed by adversarial testing — is a stronger claim than something theoretically universal but verified nowhere. The verification core underneath has zero Claude Code coupling, though — see `skills/auditlane/SKILL.md` for exactly what's portable and what a new adapter for another agent host would need.

## Quickstart — see it work in 10 seconds, no API key

```bash
pip install -r requirements.txt
python demo/dress_rehearsal.py
```

This runs three full `audit_pr` scenarios (a denied claim, a resolved two-hop chain, an unreachable authorizer) entirely offline, using the fixture bank in `auditlane/calle_client.py`. No `CALLE_API_KEY`, no network access, no real phone calls.

### Web UI — Verification Ledger Dashboard

```bash
python scripts/serve_ui.py --port 8080
```

Navigate to `http://localhost:8080` for the audit ledger, multi-hop verification timelines, the organization directory, and a Voice Sandbox for direct test calls. Every real result — from any of these panels, or from the telephony-gate hook — is persisted server-side to `.auditlane_ledger.json`, not just held in browser memory.

### Enabling the automatic command gate

Register the hook in `.claude/settings.json` (already done in this repo):

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "python \"${CLAUDE_PROJECT_DIR}/hooks/pretooluse_telephony_gate.py\"",
        "timeout": 300
      }]
    }]
  }
}
```

Then set who has to answer for a dangerous command:

```bash
export AUDITLANE_HOOK_AUTHORIZER="the security lead"   # a phonebook.json key
```

Leave it unset and the gate fails closed on every dangerous match — it never silently allows just because nobody configured an authorizer.

**Preview any claim before spending a real call:**

```bash
python scripts/run_verification.py --dry-run --title "..." --body "..."
```

Prints the exact phone number, region, and prompt CALL-E would receive — zero API calls, zero cost.

Run the test suite:

```bash
python -m pytest tests/ -v
```

### Going live

Live calls are **off by default** (`AUDITLANE_DRESS_REHEARSAL=true`). To place real calls:

```bash
pip install calle-ai
export AUDITLANE_DRESS_REHEARSAL=false
export CALLE_API_KEY=your_real_key
```

A local call-budget guard (`AUDITLANE_MAX_LIVE_CALLS`, default 3) caps live calls placed per session, tracked on disk independent of CALL-E's own balance — a retry loop or a misconfiguration can't silently run up real charges. Raise it explicitly, or delete `.auditlane_call_budget.json`, when you actually mean to place more.

Read **[docs/SAFETY.md](docs/SAFETY.md)** first — this makes real phone calls to real people, and can block real commands from executing.

### Wiring `audit_pr` into a repo

See `action.yml` and `.github/workflows/` — runs on every PR, posts the verdict as a comment, sets a commit status. Dress rehearsal stays on until a repository variable and a secret are both explicitly set.

## Project layout

```
auditlane/
  claim_extractor.py    Rule-based extraction of verbal-authorization claims
  danger_patterns.py     22-category regex detection for telephony-gate
  calle_client.py        CALL-E task/schema builders + real SDK client + mock backend
  entailment.py           Heuristic (default) and optional transformer NLI engines
  verifier.py             Multi-hop orchestration + fail-closed decision policy
  attestation.py          HMAC-signed cryptographic voice attestations
  mcp_server.py           MCP tool surface (telephony_verify_action, audit_pr_verbal_claims)
  github_integration.py   Post verdict as PR comment / commit status
  models.py, config.py    Data classes and environment-driven configuration
hooks/pretooluse_telephony_gate.py   The Claude Code PreToolUse hook itself
scripts/
  run_verification.py     CLI entry point for audit_pr (used by the GitHub Action)
  serve_ui.py              Web dashboard + REST API
  git_voice_blame.py        Query voice attestations by commit SHA
demo/dress_rehearsal.py     Zero-setup, offline, three-scenario walkthrough
web/                         Verification Ledger Dashboard frontend
tests/                       129 unit/integration/stress tests, all offline
docs/SAFETY.md                Read before ever going live
docs/RUBRIC_MAPPING.md         How this maps to the hackathon's judging criteria
skills/auditlane/            Packaged as a reusable Agent Skill contribution
.claude/settings.json          Hook registration
```

## Extension points (not built, deliberately out of scope)

- **LLM-based claim extraction** for higher recall on messier phrasing than the current regex extractor handles (see the module docstring in `claim_extractor.py` for its known scope limits).
- **Fanning out multiple claims per PR** — `audit_pr` currently audits the first claim found per run to keep output readable; the data model (`extract_claims` returns a list) already supports auditing all of them.
- **A real org-directory integration** instead of a flat JSON phonebook file.
- **True per-authorizer rate limiting** — the current call-budget guard is a global session cap, not yet "no more than N calls to the same specific person per day."
- **Adapters for other agent hosts** — the verification core has zero Claude Code coupling; `telephony-gate`'s enforcement point specifically does not (that's what makes it real). Porting the interception layer to another agent host's equivalent hook mechanism is new adapter code, not a rewrite.

## Known limitations, stated plainly

- The rule-based extractor is tuned for common phrasings and will miss more creative ones — false negatives, not false positives, are the expected failure mode for `audit_pr`, which is the safer direction to err in.
- `danger_patterns.py` is deliberately biased the opposite way — toward over-matching. A false positive there costs one phone call; a false negative is the failure mode that actually matters for a safety gate.
- The heuristic entailment engine is a deliberately simple lexical-overlap approximation, not a claim of state-of-the-art NLI accuracy. It defaults to "neutral" / defer-to-human when unsure rather than confidently wrong.
- The phonebook must be maintained separately from anything untrusted — AuditLane never dials a number derived from the PR text being audited or the command being gated (see `docs/SAFETY.md`).

## Why this, and not something else

Everything else in this space that we could find — approval-gate tools, diff-review bots, turn-end checks that compare an agent's claims to its own tool-call logs — verifies against a *digital* artifact, or trusts the agent to voluntarily ask first. None of them phone the person, and none of them sit in the agent's own execution path where asking isn't optional. AuditLane does both: it's built for the one claim category that was never going to have a digital trail, and for the one enforcement point an agent can't talk its way around.
