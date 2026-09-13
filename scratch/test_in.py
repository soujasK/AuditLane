import sys
sys.path.insert(0, 'c:/Users/kudch/Downloads/chrono-audit')
from chrono_audit.config import Config
from calle import CalleClient

client = CalleClient(api_key=Config.from_env().calle_api_key)
print("Testing IN region...")
call = client.calls.create_and_wait(
    task="say hello",
    recipients=[{"phones": ["+919867579214"], "region": "IN"}],
)
print("Result:", call.get("structured_result"))
