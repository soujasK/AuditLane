# AuditLine: The Cryptographic Telephony Verification Ledger for Autonomous AI Agents

> **Submission for the CALL-E Hackathon**  
> **Category Target:** Most Practical and Innovative Solution  
> **Live Demo:** `http://127.0.0.1:8080` | **MCP Server:** `auditline.mcp_server` | **CLI Tools:** `telephony-sudo`, `git voice-blame`

---

## 1. Executive Summary & The Problem

Autonomous software engineering agents (Devin, Claude Code, SWE-agent, Cursor) are writing and committing production code at superhuman speeds. However, they routinely make undocumented, unverifiable verbal claims in pull request descriptions and commit messages:

> *"As confirmed with @sarah_dba during morning standup, dropping the legacy v1_accounts table is safe."*  
> *"The architect verbally cleared this breaking schema change on a quick huddle."*

In enterprise software engineering, this is a catastrophic security and compliance blindspot:
1. **Hallucinated Approvals**: The agent may have confabulated the conversation entirely to resolve its task objective.
2. **Convenient Assumptions**: The human may have said *"maybe later"*, which the agent parsed as affirmative consent.
3. **Zero Audit Trail**: If a database is dropped or an IAM policy is blown away, there is zero verifiable record of who authorized what.

**AuditLine** bridges the physical and digital divide. It turns verbal conversations into verifiable, tamper-evident cryptographic ledgers by placing autonomous phone calls via CALL-E before pull requests merge or destructive CLI commands execute.

---

## 2. Core Innovations & Technical Breakthroughs

### A. Forensic Open-Recall-First Interrogation
Traditional AI verification asks leading questions: *"Did you tell Devin to drop the database?"* Cognitive psychology and police interview science prove that humans reflexively answer *"Yes"* to leading questions.
AuditLine implements a strict two-step protocol:
1. **Step 1 (Open Free-Recall)**: CALL-E calls the authorizer and asks: *"What did you discuss or approve recently regarding database tables?"* The human must state the decision in their own unprompted words.
2. **Step 2 (Recognition & NLI Entailment)**: Only if recall is ambiguous does CALL-E read the specific claim. The resulting transcript is fed into Natural Language Inference (NLI) entailment engines to compute strict logical entailment scores against the PR text.

### B. `telephony-sudo`: 2-Factor Out-of-Band Telephony Authentication for Agent CLI
When an agent like Claude Code or Devin attempts a high-blast-radius terminal command (`DROP DATABASE`, `terraform destroy`, `aws iam delete-role`):
- `telephony-sudo` intercepts the process and issues a process freeze (`SIGSTOP`).
- An anti-spoofing challenge nonce (e.g. *"Meridian-42"*) is generated.
- CALL-E dials the on-call engineer's mobile phone.
- If the engineer verbally confirms with the nonce, the command unfreezes and executes with exit code 0.
- If denied, `telephony-sudo` issues `SIGKILL` (Exit code 1) and writes a tamper-evident denial log.

### C. Cryptographic Voice Attestations & `git voice-blame`
Every successful verbal verification mints a canonical **Voice Attestation**:
- Signed using **HMAC-SHA256** over canonical JSON payloads (Commit SHA, PR Ref, Audio SHA-256 digest, Authorizer phone hash, Call duration, Timestamp).
- Persisted immutably in git metadata (`refs/notes/auditline`).
- Engineers can run `git voice-blame --commit <sha>` or inspect lines in the IDE to view the exact audio hash, authorizer phone provenance, and verbal clearance transcript.

### D. Voice-to-Diff Healing (Verbal Amendments -> Code Patches)
When an authorizer contradicts an agent's claim but provides verbal corrective guidance:
> *"No — we actually agreed to keep v1_accounts for backward compatibility until the Q3 migration finishes."*

AuditLine doesn't just block the PR; it extracts the spoken constraint and synthesizes a corrective `git diff` patch proposal right in the compliance console, allowing maintainers to apply the authorizer's spoken intent with one click.

### E. Multi-Hop Delegation Chain Resolution
Engineers often delegate: The architect says *"Yes, because the security lead approved it."* AuditLine dynamically discovers secondary authorizers, traverses the authorization graph, calls the security lead, and only issues `VERIFIED` when every hop in the chain is confirmed.

### F. Model Context Protocol (MCP) Server
Native JSON-RPC 2.0 MCP server exposing tools directly to Claude Code, Cursor, and ChatGPT:
- `telephony_verify_action`: Intercept agent tools before execution.
- `audit_pr_verbal_claims`: Run full NLI telephony audits on any pull request.
- `voice_blame_commit`: Retrieve cryptographic provenance for any commit.
- `list_directory_authorizers`: Query verified contacts.

---

## 3. Architecture Diagram

```
+-----------------------------------------------------------------------------+
|                        AUTONOMOUS CODING AGENT                               |
|                     (Claude Code / Devin / Cursor)                          |
+------------------------------------+----------------------------------------+
                                     |
                [A] Opens PR with    | [B] Attempts Destructive CLI Command
                Verbal Claims        |     (DROP DATABASE / terraform destroy)
                                     v
+------------------------------------+----------------------------------------+
|                                                                             |
|                            AuditLine ENGINE                              |
|                                                                             |
|   1. Claim Extractor: NLP extraction of authorizer, subject, action         |
|   2. Directory Anti-Spoofing: Internal phonebook lookup (no PR spoofing)    |
|   3. Challenge Nonce Generator: Ephemeral replay-prevention tokens          |
|                                                                             |
+------------------------------------+----------------------------------------+
                                     |
                                     v Outbound API (E.164)
+------------------------------------+----------------------------------------+
|                          CALL-E TELEPHONY SDK                               |
|        - Outbound SIP Trunking & Low-Latency Neural Voice Agent             |
|        - Forensic Protocol: Open Free-Recall -> Direct Entailment           |
+------------------------------------+----------------------------------------+
                                     |
                                     v Cellular Network
+------------------------------------+----------------------------------------+
|                      HUMAN AUTHORIZER'S MOBILE PHONE                         |
|             (Staff DBA / Principal Architect / Security Lead)               |
+------------------------------------+----------------------------------------+
                                     |
                                     v Structured Call Transcript & Audio Digest
+------------------------------------+----------------------------------------+
|                      ENTROPY & VERDICT PIPELINE                             |
|                                                                             |
|   1. NLI Entailment: Cross-Encoder / Heuristic Contradiction Check         |
|   2. Multi-Hop Graph: Traverses delegated authorizer references             |
|   3. Voice-to-Diff: Synthesizes code patches from verbal amendments        |
|   4. Attestation Engine: HMAC-SHA256 signature -> refs/notes/auditline   |
|                                                                             |
+------------------------------------+----------------------------------------+
                                     |
         +---------------------------+----------------------------+
         |                                                        |
         v                                                        v
+----------------------------------+    +-------------------------------------+
|      VERIFICATION LEDGER UI      |    |        GIT & CI/CD ENFORCEMENT      |
|  - Real-Time Audit Console       |    |  - GitHub Actions Merge Gate Check  |
|  - telephony-sudo Terminal       |    |  - git voice-blame CLI Inspector    |
|  - Live Voice Call Sandbox       |    |  - MCP Server for Claude Code       |
|  - Audio Waveform Player         |    |  - Auto-Diff Branch Patcher         |
+----------------------------------+    +-------------------------------------+
```

---

## 4. Two-Minute Video Demo Pitch Script

**[0:00 - 0:25] The Problem Hook**
* *Visual*: Terminal screen showing an autonomous coding agent (Claude Code / Devin) opening PR #482: *"Drop legacy v1_accounts table. Confirmed with @sarah_dba during standup."*
* *Voiceover*: "Autonomous AI coding agents are writing massive amounts of code. But what happens when an agent hallucinates human verbal permission to drop a production database table? Until today, CI systems had zero way to verify spoken words."

**[0:25 - 0:50] The Solution & Live Call**
* *Visual*: Switch to AuditLine Verification Ledger UI (`http://127.0.0.1:8080`). Show PR #482 flagged. Click into Live Voice Sandbox. Enter real phone number. Click "Call My Phone Now via CALL-E".
* *Voiceover*: "Enter AuditLine. The moment an agent claims verbal sign-off, AuditLine halts CI and places a call to Sarah's verified phone number using CALL-E. It uses forensic open-recall interviewing: it doesn't lead the witness, but asks what she approved."

**[0:50 - 1:15] Denial & Voice-to-Diff Healing**
* *Visual*: Phone rings on camera. Sarah answers: *"No — we agreed to keep v1_accounts for backward compatibility until Q3!"*
* *Visual*: UI instantly updates to `BLOCKED`. Show the Audio Waveform Player and the Voice-to-Diff Healing card displaying the exact green/red patch preserving the table.
* *Voiceover*: "Sarah denies the claim and provides guidance. AuditLine blocks the merge, logs the audio hash, and uses Voice-to-Diff to synthesize the exact patch Sarah verbally requested."

**[1:15 - 1:40] `telephony-sudo` & Real-Time CLI Interception**
* *Visual*: Switch to the `telephony-sudo` tab in the web console or bash terminal. Execute `telephony-sudo --cmd "DROP DATABASE prod_accounts;" --authorizer "@sarah_dba"`.
* *Visual*: Terminal displays `[telephony-sudo] INTERCEPTED: High-blast-radius command. FROZEN. Awaiting verbal clearance...` Phone rings, authorization is rejected, and the command is killed with `SIGKILL`.
* *Voiceover*: "For terminal agents, AuditLine introduces `telephony-sudo`. Any high-blast-radius command freezes execution until the engineer verbally authorizes it on the phone with an anti-spoofing nonce."

**[1:40 - 2:00] Cryptographic Attestation & Conclusion**
* *Visual*: Run `git voice-blame --commit HEAD` showing the HMAC-SHA256 signature and git notes provenance.
* *Voiceover*: "When approved, every verbal clearance is signed with HMAC-SHA256 and stored permanently in git notes, inspectable via `git voice-blame` and accessible via MCP in Claude Code. AuditLine: The missing trust layer for autonomous software engineering."

---

## 5. Hackathon Judging Matrix Alignment

| Criteria | How AuditLine Delivers |
| :--- | :--- |
| **Impactful Business Use Case** | Solves the #1 blocker for enterprise AI agent autonomy: unverified human verbal claims and hallucinated permissions in high-stakes codebases. |
| **Technical Depth & Innovation** | Combines CALL-E telephony, forensic free-recall interrogation, NLI entailment scoring, process-freezing CLI interception (`telephony-sudo`), cryptographic HMAC attestations, Voice-to-Diff code healing, and MCP server. |
| **Completeness & Polish** | 100% test coverage (26/26 automated tests passing), upstream validation passing, live telephone dispatching, and a high-density "Verification Ledger" enterprise web UI. |
| **Safety & Fail-Closed Design** | Strict internal phonebook directory (never dials phone numbers from PR text), rate-limiting, anti-spoofing challenge nonces, and dress rehearsal zero-cost simulation defaults. |
