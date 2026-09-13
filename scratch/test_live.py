import sys
import traceback
sys.path.insert(0, '.')
from chrono_audit.config import Config
from chrono_audit.calle_client import CalleVerificationClient
from chrono_audit.models import Claim

base_cfg = Config.from_env()
call_cfg = Config(
    dress_rehearsal=False,
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
    print("Making live call...")
    res = client.verify_claim(claim, "+14013586178")
    print(res)
except Exception as e:
    traceback.print_exc()
