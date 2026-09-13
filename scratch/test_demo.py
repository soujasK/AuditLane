import sys
sys.path.insert(0, 'c:/Users/kudch/Downloads/chrono-audit')
from chrono_audit.config import Config
from chrono_audit.models import Claim
from chrono_audit.calle_client import CalleVerificationClient

print("Starting live SDK test with 2ndLine number...")
client = CalleVerificationClient()
claim = Claim(
    authorizer_name="Lead Database Engineer", 
    claim_text="I am executing a destructive DROP TABLE command on the production legacy_auth_tokens database. I confirmed with the Lead Database Engineer during our morning sync that this data is fully migrated and safe to delete.", 
    subject="DROP TABLE legacy_auth_tokens", 
    source_line="I am executing a destructive DROP TABLE command"
)
try:
    print("Placing call to +14013586178...")
    result = client.verify_claim(claim, "+14013586178")
    print("Call finished!", result)
except Exception as e:
    print("Failed to place call:", e)
