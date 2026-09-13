#!/usr/bin/env python3
"""
AuditLine Model Context Protocol (MCP) Server.

Enables Claude Code, Cursor, Codex, and other MCP-compliant autonomous agent
environments to natively perform out-of-band telephony verifications, inspect
Git voice attestations, and gate tool execution.

Transport: JSON-RPC 2.0 over standard I/O (stdio).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from auditline.attestation import create_voice_attestation, load_attestation, save_attestation
from auditline.calle_client import CalleVerificationClient
from auditline.config import Config
from auditline.models import Claim, Confirmation
from auditline.verifier import ChronoAuditor


def load_phonebook() -> Dict[str, str]:
    path = ROOT_DIR / "phonebook.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
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


def handle_tools_list() -> List[Dict[str, Any]]:
    return [
        {
            "name": "audit_pr_verbal_claims",
            "description": "Scans pull request text for verbal authorization claims and executes telephony verification.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "PR title"},
                    "body": {"type": "string", "description": "PR description or commit message body"},
                    "pr_ref": {"type": "string", "description": "Repository and PR number, e.g. org/repo#42"},
                },
                "required": ["title", "body"],
            },
        },
        {
            "name": "telephony_verify_action",
            "description": "Places a synchronous CALL-E verification call to an authorizer before executing a high-stakes action.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "authorizer": {"type": "string", "description": "Name or handle of person to call"},
                    "action_description": {"type": "string", "description": "Specific action to authorize"},
                },
                "required": ["authorizer", "action_description"],
            },
        },
        {
            "name": "voice_blame_commit",
            "description": "Queries the cryptographic voice attestation associated with a Git commit SHA.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "commit_sha": {"type": "string", "description": "Commit SHA or hash"},
                },
                "required": ["commit_sha"],
            },
        },
        {
            "name": "list_directory_authorizers",
            "description": "Lists verified organization contacts recognized by AuditLine.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
    ]


def handle_tool_call(name: str, arguments: Dict[str, Any]) -> str:
    phonebook = load_phonebook()

    if name == "audit_pr_verbal_claims":
        title = arguments.get("title", "")
        body = arguments.get("body", "")
        pr_ref = arguments.get("pr_ref", "mcp-agent-pr#01")
        auditor = ChronoAuditor(phonebook=phonebook)
        outcome = auditor.audit_pr(pr_ref, title, body)
        return outcome.to_markdown()

    elif name == "telephony_verify_action":
        authorizer = arguments.get("authorizer", "").strip()
        action = arguments.get("action_description", "").strip()
        phone = phonebook.get(authorizer.lower())
        if not phone:
            return f"VERIFICATION REJECTED: No phone number on file for '{authorizer}'. Fails closed."

        client = CalleVerificationClient(Config.from_env())
        claim = Claim(
            authorizer_name=authorizer,
            claim_text=f"Authorize action: '{action}'",
            subject=action,
            source_line=action,
        )
        res = client.verify_claim(claim, phone)
        if res.direct_confirmation == Confirmation.CONFIRMED:
            attest = create_voice_attestation(
                commit_sha="mcp_action",
                pr_reference="mcp-session",
                authorizer_name=authorizer,
                phone_number=phone,
                statement=res.authorizer_statement,
                verdict="VERIFIED",
            )
            save_attestation(attest, base_dir=ROOT_DIR)
            return (
                f"VERIFIED: {authorizer} confirmed on the phone.\n"
                f"Statement: \"{res.authorizer_statement}\"\n"
                f"Attestation ID: {attest.attestation_id}"
            )
        elif res.direct_confirmation == Confirmation.DENIED:
            return f"BLOCKED: {authorizer} explicitly denied authorization.\nStatement: \"{res.authorizer_statement}\""
        else:
            return f"NEEDS_HUMAN_REVIEW: Contact {authorizer} was ambiguous or unreachable."

    elif name == "voice_blame_commit":
        sha = arguments.get("commit_sha", "").strip()
        attest = load_attestation(sha, base_dir=ROOT_DIR)
        if not attest:
            return f"No voice attestation found for commit '{sha}'."
        return json.dumps(attest.to_dict(), indent=2)

    elif name == "list_directory_authorizers":
        contacts = [{"name": k, "masked_phone": v[:3] + " ••• " + v[-4:] if len(v) > 6 else v} for k, v in phonebook.items()]
        return json.dumps(contacts, indent=2)

    return f"Unknown tool: {name}"


def run_mcp_server():
    """Reads JSON-RPC lines from stdin and writes responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        msg_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "auditline-mcp",
                        "version": "1.0.0",
                    },
                    "capabilities": {
                        "tools": {},
                    },
                },
            }
        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": handle_tools_list(),
                },
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            output_text = handle_tool_call(tool_name, tool_args)
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": output_text,
                        }
                    ]
                },
            }
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    run_mcp_server()
