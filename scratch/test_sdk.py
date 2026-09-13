import sys
sys.path.insert(0, 'c:/Users/kudch/Downloads/chrono-audit')
from chrono_audit.config import Config
from chrono_audit.models import Claim
from chrono_audit.calle_client import CalleVerificationClient

print("Starting live SDK test...")
client = CalleVerificationClient()
claim = Claim(
    authorizer_name="Hackathon Judge", 
    claim_text="Testing live call", 
    subject="SDK Check", 
    source_line="Testing live call"
)
try:
    print("Placing call to +919867579214...")
    result = client.verify_claim(claim, "+919867579214")
    print("Call finished!", result)
except Exception as e:
    print("Failed to place call:", e)
