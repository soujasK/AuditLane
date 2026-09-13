from chrono_audit.config import Config
from chrono_audit.calle_client import CalleVerificationClient
from chrono_audit.models import Claim

base_cfg = Config.from_env()
call_cfg = Config(
    dress_rehearsal=True,
    calle_api_key=base_cfg.calle_api_key,
    calle_base_url=base_cfg.calle_base_url,
    entailment_confidence_threshold=base_cfg.entailment_confidence_threshold,
    max_hops=base_cfg.max_hops,
    max_call_duration_seconds=base_cfg.max_call_duration_seconds,
)

client = CalleVerificationClient(call_cfg)
claim = Claim(
    authorizer_name="Judge",
    claim_text="Verbal authorization test",
    subject="Production authorization check",
    source_line="Verbal authorization test",
)

try:
    res = client.verify_claim(claim, "+15555550192")
    print(res.direct_confirmation.value)
    import hashlib
    print(res.audio_sha256 or hashlib.sha256("Verbal authorization test".encode()).hexdigest())
    print(res.call_uuid or f"call_{abs(hash('Verbal authorization test')) % 90000 + 10000}")
except Exception as e:
    import traceback
    traceback.print_exc()
