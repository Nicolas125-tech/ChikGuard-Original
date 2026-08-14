import urllib.request
import json

data = json.dumps({
    "memory": "submit"
}).encode('utf-8')

req = urllib.request.Request(
    'http://localhost:8080/submit',
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
