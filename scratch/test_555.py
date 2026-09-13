import urllib.request
import json
req = urllib.request.Request(
    'http://127.0.0.1:8080/api/test-call',
    data=b'{"name": "Judge", "phone": "+15555550192", "claim": "Verbal authorization test"}',
    headers={'Content-Type': 'application/json'}
)
try:
    res = urllib.request.urlopen(req)
    print(res.read())
except Exception as e:
    print(e)
    print(e.read())
