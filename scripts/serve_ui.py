#!/usr/bin/env python3
"""
Lightweight web server for AuditLane Verification Ledger UI.
Serves static assets from web/ directory and provides REST endpoints:
- GET  /api/status
- GET  /api/phonebook
- POST /api/phonebook
- POST /api/audit (runs real Python AuditLaneVerifier on PR text)
"""

from __future__ import annotations

import argparse
import base64
import functools
import hmac
import hashlib
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler
from urllib.parse import urlsplit, parse_qs
import socketserver

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")
PHONEBOOK_PATH = os.path.join(BASE_DIR, "phonebook.json")

# Explicit, unconditional -- previously this relied on some other code
# path (e.g. Config.from_env(), called from inside a POST handler)
# happening to run first and load .env as a side effect. If /api/ledger
# (a plain GET reading os.environ directly for GITHUB_TOKEN) was the
# first endpoint hit in a fresh server process, .env was never loaded
# and it silently saw nothing. Load it here, once, unconditionally, so
# every handler can rely on it regardless of request order.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

# call_id -> True once a streamed live call has been finalized (parsed,
# ledger-appended). Guards against double-appending the same result if
# the frontend's poll loop checks status more than once after the call
# already reached a terminal state. In-memory only, resets on restart —
# fine for a single demo session; a call that outlives a restart just
# stops being pollable, same as it would with the old blocking flow.
_finalized_live_calls: set[str] = set()

# call_id -> {name, phone, claim_text} recorded at /api/live-call/start
# time. CALL-E's call object doesn't carry the original clean claim text
# back (only the full constructed task prompt), so this is kept
# server-side to build an accurate ledger entry once the call finishes.
_pending_live_calls: dict[str, dict] = {}

# Ensure auditlane package is importable
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from auditlane.claim_extractor import extract_claims_from_pr
from auditlane.config import Config
from auditlane.verifier import AuditLaneVerifier
from auditlane.models import VerificationOutcome, Confirmation, EntailmentLabel, Verdict, Claim
from auditlane.calle_client import CalleVerificationClient
from auditlane.github_integration import post_pr_comment, set_commit_status
from auditlane.github_ledger_sync import fetch_github_audit_entries
from auditlane.ledger import load_ledger, append_ledger, LEDGER_PATH

# audit_pr runs on GitHub's own remote runners, not this machine, so it
# has no local ledger to write to -- see auditlane/github_ledger_sync.py.
# Cached with a short TTL rather than hit the GitHub API on every
# /api/ledger poll (the dashboard polls every 5s on its own).
_GITHUB_LEDGER_CACHE: dict = {"entries": [], "fetched_at": 0.0}
_GITHUB_LEDGER_TTL_SEC = 15


def _get_github_ledger_entries() -> list[dict]:
    import time
    now = time.time()
    if now - _GITHUB_LEDGER_CACHE["fetched_at"] < _GITHUB_LEDGER_TTL_SEC:
        return _GITHUB_LEDGER_CACHE["entries"]

    token = os.environ.get("GITHUB_TOKEN", "")
    repos = [r for r in os.environ.get("AUDITLANE_WATCH_REPOS", "").split(",") if r.strip()]
    entries = fetch_github_audit_entries(token, repos) if (token and repos) else []
    _GITHUB_LEDGER_CACHE["entries"] = entries
    _GITHUB_LEDGER_CACHE["fetched_at"] = now
    return entries


def _resolve_audit_config(base_cfg: Config, phonebook: dict, title: str, body: str) -> Config:
    """Mirrors the same live/demo heuristic /api/test-call already uses:
    if the PR text's authorizer resolves to a "555" demo/fixture number
    (or nobody's on file), force dress-rehearsal for THIS request so the
    built-in demo presets always render a clean result instead of trying
    a real call to a fake number and surfacing a raw CALL-E error. A real
    authorizer with a real phone number still goes live exactly as
    configured in .env — this only protects the canned demo scenarios.
    """
    claims = extract_claims_from_pr(title, body)
    phone = phonebook.get(claims[0].authorizer_name.strip().lower()) if claims else None
    is_live = bool(phone) and ("555" not in phone) and bool(base_cfg.calle_api_key) and not base_cfg.dress_rehearsal
    if is_live:
        return base_cfg
    return Config(
        dress_rehearsal=True,
        calle_api_key=base_cfg.calle_api_key,
        calle_base_url=base_cfg.calle_base_url,
        entailment_confidence_threshold=base_cfg.entailment_confidence_threshold,
        max_hops=base_cfg.max_hops,
        max_call_duration_seconds=base_cfg.max_call_duration_seconds,
        max_live_calls=base_cfg.max_live_calls,
        github_token=base_cfg.github_token,
        github_repo=base_cfg.github_repo,
    )


def load_phonebook() -> dict[str, str]:
    if os.path.exists(PHONEBOOK_PATH):
        try:
            with open(PHONEBOOK_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {k.lower(): str(v) for k, v in data.items() if not k.startswith("_")}
        except Exception:
            pass
    return {
        "@sarah_dba": "+1 415 555 0192",
        "sarah": "+1 415 555 0192",
        "the architect": "+1 206 555 0148",
        "the security lead": "+1 650 555 0173",
        "elena rostova": "+1 408 555 0115",
    }


def save_phonebook(data: dict[str, str]) -> None:
    with open(PHONEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# load_ledger / append_ledger / LEDGER_PATH now live in auditlane/ledger.py
# (imported above) so the dashboard and hooks/pretooluse_telephony_gate.py
# share exactly one ledger implementation instead of two that could drift.


def _finalize_live_call(client: CalleVerificationClient, call: dict, call_id: str) -> dict:
    """Parses a terminal (completed/failed/canceled) raw CALL-E call
    object into the same response shape the old blocking /api/test-call
    already returns, and appends the real ledger entry exactly once even
    if the frontend's poll loop checks status again after the call is
    already done."""
    res = client.parse_call_result(call)
    meta = _pending_live_calls.get(call_id, {})
    name = meta.get("name") or call.get("metadata", {}).get("authorizer", "Unknown")
    phone = meta.get("phone", "")
    claim_text = meta.get("claim_text", "")

    resp_data = {
        "authorizer": name,
        "phone": phone,
        "durationSec": res.call_duration_seconds,
        "reached": res.reachable,
        "statement": res.authorizer_statement,
        "confirmation": res.direct_confirmation.value,
        "audio_sha256": res.audio_sha256 or None,
        "call_uuid": res.call_uuid or None,
    }

    if call_id not in _finalized_live_calls:
        _finalized_live_calls.add(call_id)
        verdict = ("VERIFIED" if res.direct_confirmation == Confirmation.CONFIRMED
                   else ("BLOCKED" if res.direct_confirmation == Confirmation.DENIED else "NEEDS_HUMAN_REVIEW"))
        append_ledger({
            "id": "sbx_" + (res.call_uuid or call_id),
            "prRef": "voice-sandbox#" + call_id[-8:],
            "title": "Voice Sandbox Test Call (live stream)",
            "body": claim_text,
            "commitSha": (res.call_uuid or call_id).replace("_", "")[:10],
            "authorizer": name,
            "timestamp": "Just now",
            "verdict": verdict,
            "reason": f"Voice Sandbox direct call — no PR claim extraction or entailment scoring applied. Raw CALL-E confirmation: {res.direct_confirmation.value}.",
            "policy": "Voice Sandbox — Direct Call Test",
            "engine": "n/a (raw call, no entailment)",
            "hops": [{
                "hopIndex": 0,
                "authorizer": name,
                "role": "Sandbox Test Contact",
                "phone": phone or "n/a",
                "reached": bool(res.reachable),
                "durationSec": res.call_duration_seconds,
                "claimText": claim_text,
                "statement": res.authorizer_statement,
                "confirmation": res.direct_confirmation.value,
                "entailmentResult": "n/a",
                "confidence": "n/a",
                "engine": "n/a",
                "callUuid": res.call_uuid or None,
                "audioSha256": res.audio_sha256 or None,
            }],
        })
        _pending_live_calls.pop(call_id, None)

    return resp_data


def outcome_to_dict(outcome: VerificationOutcome, title: str, body: str, pr_ref: str) -> dict:
    hops_data = []
    for i, hop in enumerate(outcome.hops):
        call_res = hop.call_result
        ent_res = hop.entailment
        hops_data.append({
            "hopIndex": i,
            "authorizer": hop.claim.authorizer_name,
            "role": "Verified Contact",
            "phone": "Registered on file" if call_res and call_res.reachable else "Not in directory",
            "reached": call_res.reachable if call_res else False,
            "durationSec": call_res.call_duration_seconds if call_res else 0,
            "claimText": hop.claim.claim_text,
            "statement": call_res.authorizer_statement if call_res else "[No statement received]",
            "confirmation": call_res.direct_confirmation.value if call_res else "unclear",
            "entailmentResult": ent_res.label.value if ent_res else "neutral",
            "confidence": f"{ent_res.confidence:.2f}" if ent_res else "0.00",
            "engine": ent_res.engine if ent_res else "none",
            # Real per-hop identifiers when a live call actually happened;
            # None in dress rehearsal, honestly, rather than fabricated.
            "callUuid": (call_res.call_uuid or None) if call_res else None,
            "audioSha256": (call_res.audio_sha256 or None) if call_res else None,
        })

    primary_authorizer = outcome.hops[0].claim.authorizer_name if outcome.hops else "Unknown"

    return {
        "id": f"aud_{abs(hash(pr_ref + title + body)) % 9000 + 1000}",
        "prRef": pr_ref or "custom-repo#100",
        "title": title,
        "body": body,
        "commitSha": f"{abs(hash(body)) & 0xffffffffff:010x}",
        "authorizer": primary_authorizer,
        "timestamp": "Just now",
        "verdict": outcome.verdict.value.upper(),
        "reason": outcome.reason,
        "policy": "Fail-Closed Verification Policy",
        "engine": outcome.hops[0].entailment.engine if outcome.hops and outcome.hops[0].entailment else "Heuristic-v1",
        "hops": hops_data,
        # The real attestation, when one was actually created and signed
        # (see auditlane/attestation.py) — was previously dropped here
        # entirely, so the frontend displayed a hardcoded fake hash
        # identical for every single VERIFIED result instead of this.
        "attestation_id": outcome.attestation_id,
    }


class AuditLaneHandler(SimpleHTTPRequestHandler):
    def _send_json(self, obj, status: int = 200) -> None:
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _check_auth(self) -> bool:
        """HTTP Basic Auth gate, required for anything beyond local-only
        use. Every endpoint here is unauthenticated by design for local
        dev (matches how this project has always run), but this server
        has real, spendable CALL-E credentials behind it once configured
        for live calls -- Voice Sandbox alone lets any caller dial any
        number. AUDITLANE_DASHBOARD_PASSWORD being unset means "local
        machine only, trusted by definition" and skips this entirely;
        set it before ever putting this behind a public URL.
        """
        required_password = os.environ.get("AUDITLANE_DASHBOARD_PASSWORD", "")
        if not required_password:
            return True  # no password configured -- local-only trust model, unchanged

        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[len("Basic "):]).decode("utf-8")
                _, _, supplied_password = decoded.partition(":")
            except Exception:
                supplied_password = ""
        else:
            supplied_password = ""

        if hmac.compare_digest(supplied_password, required_password):
            return True

        body = b"Authentication required."
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="AuditLane Dashboard"')
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return False

    def do_GET(self):
        if not self._check_auth():
            return
        split = urlsplit(self.path)
        path = split.path
        query = parse_qs(split.query)

        if path == "/api/status":
            cfg = Config.from_env()
            self._send_json({
                "status": "online",
                "dress_rehearsal": cfg.dress_rehearsal,
                "has_api_key": bool(cfg.calle_api_key),
                "entailment_threshold": cfg.entailment_confidence_threshold,
                "max_hops": cfg.max_hops,
                "max_call_seconds": cfg.max_call_duration_seconds,
            })
            return
        elif path == "/api/phonebook":
            self._send_json(load_phonebook())
            return
        elif path == "/api/ledger":
            merged = _get_github_ledger_entries() + load_ledger()
            self._send_json(merged)
            return
        elif path == "/api/live-call/events":
            call_id = (query.get("call_id") or [""])[0]
            cursor = (query.get("cursor") or [None])[0]
            if not call_id:
                self._send_json({"error": "call_id is required"}, status=400)
                return
            try:
                client = CalleVerificationClient(Config.from_env())
                events = client.get_call_events(call_id, cursor=cursor)
                self._send_json(events)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return
        elif path == "/api/live-call/status":
            call_id = (query.get("call_id") or [""])[0]
            if not call_id:
                self._send_json({"error": "call_id is required"}, status=400)
                return
            try:
                client = CalleVerificationClient(Config.from_env())
                call = client.get_call_status(call_id)
                status = call.get("status")
                terminal = status in {"completed", "failed", "canceled"}
                resp = {"status": status, "terminal": terminal}
                if terminal:
                    resp["result"] = _finalize_live_call(client, call, call_id)
                self._send_json(resp)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return
        super().do_GET()

    def do_POST(self):
        # The GitHub webhook authenticates itself via its own HMAC
        # signature (X-Hub-Signature-256) below, not a browser password
        # GitHub has no way to supply -- everything else needs the gate.
        if self.path != "/api/webhook/github" and not self._check_auth():
            return
        if self.path == "/api/webhook/github":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len)
            
            # Verify HMAC signature
            secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
            if secret:
                signature_header = self.headers.get("X-Hub-Signature-256")
                if not signature_header:
                    self.send_response(401)
                    self.end_headers()
                    return
                hash_object = hmac.new(secret.encode("utf-8"), msg=raw_body, digestmod=hashlib.sha256)
                expected_signature = "sha256=" + hash_object.hexdigest()
                if not hmac.compare_digest(expected_signature, signature_header):
                    self.send_response(403)
                    self.end_headers()
                    return
            
            payload = json.loads(raw_body.decode("utf-8"))
            
            if payload.get("action") in ["opened", "synchronize"] and "pull_request" in payload:
                pr = payload["pull_request"]
                repo = payload["repository"]["full_name"]
                pr_number = pr["number"]
                title = pr.get("title", "")
                body = pr.get("body", "")
                pr_ref = f"{repo}#{pr_number}"
                commit_sha = pr["head"]["sha"]
                
                # Acknowledge webhook immediately to avoid GitHub timeout
                self.send_response(202)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "accepted"}')
                
                # Execute asynchronously (in a real app we'd use celery/redis or threading)
                import threading
                def run_audit_task():
                    try:
                        phonebook = load_phonebook()
                        auditor = AuditLaneVerifier(phonebook=phonebook)
                        outcome = auditor.audit_pr(pr_ref, title, body)
                        config = Config.from_env()
                        if config.github_token:
                            post_pr_comment(config, pr_number, outcome)
                            set_commit_status(config, commit_sha, outcome)
                    except Exception as e:
                        print(f"Webhook processing error: {e}")
                
                threading.Thread(target=run_audit_task).start()
                return

        elif self.path == "/api/audit":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            try:
                payload = json.loads(raw_body)
                title = payload.get("title", "")
                body = payload.get("body", "")
                pr_ref = payload.get("pr_ref", "manual-audit#001")
                
                # Run the actual AuditLaneVerifier pipeline!
                phonebook = load_phonebook()
                call_cfg = _resolve_audit_config(Config.from_env(), phonebook, title, body)
                auditor = AuditLaneVerifier(config=call_cfg, phonebook=phonebook)
                outcome = auditor.audit_pr(pr_ref, title, body)
                
                result = outcome_to_dict(outcome, title, body, pr_ref)
                append_ledger(result)
                data = json.dumps(result).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                err_data = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err_data)))
                self.end_headers()
                self.wfile.write(err_data)
            return
        elif self.path == "/api/phonebook":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            try:
                payload = json.loads(raw_body)
                save_phonebook(payload)
                data = json.dumps({"status": "saved"}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                err_data = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err_data)))
                self.end_headers()
                self.wfile.write(err_data)
            return
        elif self.path == "/api/live-call/start":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            try:
                payload = json.loads(raw_body)
                name = payload.get("name", "Judge")
                phone = payload.get("phone", "")
                claim_text = payload.get("claim", "Verbal authorization test")
                simulate = payload.get("simulate", False)

                base_cfg = Config.from_env()
                is_live = (not simulate) and bool(phone) and ("555" not in phone) and bool(base_cfg.calle_api_key)

                if not is_live:
                    # Nothing to stream for a mock/demo call — it resolves
                    # instantly. Frontend falls back to the existing
                    # synchronous /api/test-call instead of polling for
                    # events that will never arrive.
                    self._send_json({"mock": True})
                    return

                client = CalleVerificationClient(base_cfg)
                claim = Claim(
                    authorizer_name=name,
                    claim_text=claim_text,
                    subject=claim_text or "a recent production authorization",
                    source_line=claim_text,
                )
                call_id = client.start_live_call(claim, phone)
                _pending_live_calls[call_id] = {"name": name, "phone": phone, "claim_text": claim_text}
                self._send_json({"mock": False, "call_id": call_id})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return
        elif self.path == "/api/test-call":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            try:
                payload = json.loads(raw_body)
                name = payload.get("name", "Judge")
                phone = payload.get("phone", "")
                claim_text = payload.get("claim", "Verbal authorization test")
                simulate = payload.get("simulate", False)
                
                # Check if live call is requested
                base_cfg = Config.from_env()
                is_live = (not simulate) and bool(phone) and ("555" not in phone) and bool(base_cfg.calle_api_key)
                call_cfg = base_cfg if is_live else Config(
                    dress_rehearsal=True,
                    calle_api_key=base_cfg.calle_api_key,
                    calle_base_url=base_cfg.calle_base_url,
                    entailment_confidence_threshold=base_cfg.entailment_confidence_threshold,
                    max_hops=base_cfg.max_hops,
                    max_call_duration_seconds=base_cfg.max_call_duration_seconds,
                )
                
                client = CalleVerificationClient(call_cfg)
                claim = Claim(
                    authorizer_name=name,
                    claim_text=claim_text,
                    # Step 1's open-recall question asks about `subject`,
                    # not `claim_text` (see build_task_prompt) — this was
                    # hardcoded to a generic phrase, so the open question
                    # never actually referenced what was typed here.
                    subject=claim_text or "a recent production authorization",
                    source_line=claim_text,
                )
                res = client.verify_claim(claim, phone or "+15550001111")

                resp_data = {
                    "authorizer": name,
                    "phone": phone,
                    "durationSec": res.call_duration_seconds,
                    "reached": res.reachable,
                    "statement": res.authorizer_statement,
                    "confirmation": res.direct_confirmation.value,
                    # Previously fabricated a fake-looking hash/ID for
                    # mock results (indistinguishable from a real one in
                    # the UI). null here honestly means "no real call
                    # happened, dress rehearsal."
                    "audio_sha256": res.audio_sha256 or None,
                    "call_uuid": res.call_uuid or None,
                }
                append_ledger({
                    "id": "sbx_" + (res.call_uuid or hashlib.sha256((name + claim_text).encode()).hexdigest()[:10]),
                    "prRef": "voice-sandbox#" + hashlib.sha256((name + claim_text).encode()).hexdigest()[:8],
                    "title": "Voice Sandbox Test Call",
                    "body": claim_text,
                    "commitSha": (res.call_uuid or "sandbox").replace("_", "")[:10],
                    "authorizer": name,
                    "timestamp": "Just now",
                    "verdict": "VERIFIED" if res.direct_confirmation == Confirmation.CONFIRMED
                        else ("BLOCKED" if res.direct_confirmation == Confirmation.DENIED else "NEEDS_HUMAN_REVIEW"),
                    "reason": f"Voice Sandbox direct call — no PR claim extraction or entailment scoring applied. Raw CALL-E confirmation: {res.direct_confirmation.value}.",
                    "policy": "Voice Sandbox — Direct Call Test",
                    "engine": "n/a (raw call, no entailment)",
                    "hops": [{
                        "hopIndex": 0,
                        "authorizer": name,
                        "role": "Sandbox Test Contact",
                        "phone": phone or "n/a",
                        "reached": bool(res.reachable),
                        "durationSec": res.call_duration_seconds,
                        "claimText": claim_text,
                        "statement": res.authorizer_statement,
                        "confirmation": res.direct_confirmation.value,
                        "entailmentResult": "n/a",
                        "confidence": "n/a",
                        "engine": "n/a",
                        "callUuid": res.call_uuid or None,
                        "audioSha256": res.audio_sha256 or None,
                    }],
                })
                data = json.dumps(resp_data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                err_data = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err_data)))
                self.end_headers()
                self.wfile.write(err_data)
            return

        self.send_response(404)
        self.end_headers()


class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """A plain TCPServer handles one request at a time — a single live
    CALL-E call (which blocks synchronously in create()/wait_for_result())
    would freeze the ENTIRE app for its whole duration: every other tab,
    every other click, even just reloading the page. Threading lets a
    slow/live request run in its own thread instead of stalling the rest
    of the UI. daemon_threads=True so stray in-flight requests don't
    block process shutdown."""
    daemon_threads = True


def run(port: int = 8080, host: str = "127.0.0.1"):
    if not os.path.isdir(WEB_DIR):
        print(f"Error: web directory not found at {WEB_DIR}", file=sys.stderr)
        sys.exit(1)

    if host != "127.0.0.1" and not os.environ.get("AUDITLANE_DASHBOARD_PASSWORD"):
        print(
            "Error: refusing to bind to a non-localhost address without "
            "AUDITLANE_DASHBOARD_PASSWORD set. Every endpoint here is open "
            "by default (that's fine for 127.0.0.1, where only this machine "
            "can reach it) -- binding wider than that with no password means "
            "anyone who finds the URL can spend your real CALL-E credits via "
            "Voice Sandbox. Set the password, or keep --host at 127.0.0.1.",
            file=sys.stderr,
        )
        sys.exit(1)

    ThreadingHTTPServer.allow_reuse_address = True
    handler = functools.partial(AuditLaneHandler, directory=WEB_DIR)
    with ThreadingHTTPServer((host, port), handler) as httpd:
        print("=" * 64, flush=True)
        print(" AuditLane: Verification Ledger Web Server", flush=True)
        print("=" * 64, flush=True)
        print(f" Listening on: http://{host}:{port}", flush=True)
        print(f" Serving Directory: {WEB_DIR}", flush=True)
        print(" Connected Backend: AuditLaneVerifier Python Engine", flush=True)
        print(
            f" Dashboard password: {'SET (required)' if os.environ.get('AUDITLANE_DASHBOARD_PASSWORD') else 'not set (open access)'}",
            flush=True,
        )
        _cfg = Config.from_env()
        _key = _cfg.calle_api_key
        print(
            f" CALL-E key loaded: {_key[:14]}...{_key[-6:]} (dress_rehearsal={_cfg.dress_rehearsal})"
            if _key else " CALL-E key loaded: (none set)",
            flush=True,
        )
        print("=" * 64, flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve AuditLane Web UI with API")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--host", default="127.0.0.1", help="Address to bind (default: 127.0.0.1, local-only; use 0.0.0.0 for container/public deployment, which requires AUDITLANE_DASHBOARD_PASSWORD to be set)")
    args = parser.parse_args()
    run(port=args.port, host=args.host)
