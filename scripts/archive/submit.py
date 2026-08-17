import urllib.request
import urllib.parse
import json

def get_safe_response(url_str, payload):
    parsed = urllib.parse.urlparse(url_str)
    
    # Force HTTPS unless it's a local address for development
    if parsed.scheme != 'https' and parsed.hostname not in ('localhost', '127.0.0.1'):
        raise ValueError("Insecure transport: Only HTTPS is allowed for external requests.")
        
    # Reconstruct the URL safely to prevent parameter/CRLF injections
    safe_url = urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        safe_url,
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    with urllib.request.urlopen(req) as response:
        return response.read().decode('utf-8')

try:
    response_text = get_safe_response('http://localhost:8080/submit', {"memory": "submit"})
    print(response_text)
except Exception as e:
    print(f"Error: {e}")
