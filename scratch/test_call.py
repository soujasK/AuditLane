import urllib.request, json
req = urllib.request.Request(
    'http://127.0.0.1:8080/api/test-call', 
    data=json.dumps({"name":"Judge","phone":"+919867579214","claim":"Test claim"}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
try:
    resp = urllib.request.urlopen(req)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(e.read().decode())
