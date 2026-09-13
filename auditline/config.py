"""
All tunables live here and are read from environment variables so nothing
is hardcoded and nothing dangerous is on-by-default.

DRESS_REHEARSAL defaults to True on purpose: this project makes real phone
calls to real colleagues when it is live, so accidentally running it live
must never be the path of least resistance. See docs/SAFETY.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass



def _bool_env(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    # Safety: must be explicitly disabled to place real calls.
    dress_rehearsal: bool = True

    # CALL-E credentials / endpoint (unused in dress rehearsal mode).
    calle_api_key: str = ""
    calle_base_url: str = "https://api.heycall-e.com"

    # Verification thresholds.
    entailment_confidence_threshold: float = 0.65
    max_hops: int = 2
    max_call_duration_seconds: int = 180

    # GitHub integration (unused unless posting a real PR comment).
    github_token: str = ""
    github_repo: str = ""

    @staticmethod
    def from_env() -> "Config":
        return Config(
            dress_rehearsal=_bool_env("AUDITLINE_DRESS_REHEARSAL", True),
            calle_api_key=os.environ.get("CALLE_API_KEY", ""),
            calle_base_url=os.environ.get("CALLE_BASE_URL", "https://api.heycall-e.com"),
            entailment_confidence_threshold=float(
                os.environ.get("AUDITLINE_ENTAILMENT_THRESHOLD", "0.65")
            ),
            max_hops=int(os.environ.get("AUDITLINE_MAX_HOPS", "2")),
            max_call_duration_seconds=int(
                os.environ.get("AUDITLINE_MAX_CALL_SECONDS", "180")
            ),
            github_token=os.environ.get("GITHUB_TOKEN", ""),
            github_repo=os.environ.get("GITHUB_REPOSITORY", ""),
        )
