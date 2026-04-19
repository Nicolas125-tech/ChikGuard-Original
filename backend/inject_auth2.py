import re

auth_middleware_code = """
import jwt
from functools import wraps
from flask import request, jsonify
from supabase import create_client, Client
import os

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '') # Service role key ideally, or anon key if RLS allows
SUPABASE_JWT_SECRET = os.environ.get('SUPABASE_JWT_SECRET', '')

if SUPABASE_URL and SUPABASE_KEY:
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase_client = None

def require_auth(roles=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Missing or invalid token'}), 401
            
            token = auth_header.split(' ')[1]
            try:
                # Validate JWT
                decoded = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=['HS256'], audience='authenticated')
                user_id = decoded.get('sub')
                if not user_id:
                    return jsonify({'error': 'Invalid token payload'}), 401
                
                # Fetch profile from DB to get the reliable role and status
                if supabase_client:
                    response = supabase_client.table('profiles').select('role, status').eq('id', user_id).single().execute()
                    profile = response.data
                    if not profile:
                        return jsonify({'error': 'Profile not found'}), 403
                    if profile.get('status') == 'PENDING':
                        return jsonify({'error': 'User awaiting approval'}), 403
                        
                    user_role = profile.get('role', 'viewer').lower()
                else:
                    # Fallback if supabase client is not configured
                    user_role = decoded.get('app_metadata', {}).get('role', 'viewer').lower()

                if roles and user_role not in roles and 'admin' not in user_role and 'superadmin' not in user_role:
                    return jsonify({'error': f'Insufficient permissions. Required: {roles}'}), 403
                    
                request.user_id = user_id
                request.user_role = user_role
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token expired'}), 401
            except Exception as e:
                return jsonify({'error': str(e)}), 401
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
"""

with open('c:/nic/ChikGuard-Original/backend/app.py', 'r', encoding='utf-8') as f:
    code = f.read()

if 'def require_auth' not in code:
    insert_pos = code.find('app = Flask')
    if insert_pos == -1:
        insert_pos = code.find('def ')
        
    if insert_pos > 0:
        code = code[:insert_pos] + auth_middleware_code + "\n" + code[insert_pos:]

# Routes to protect
routes_to_protect_with_admin = [
    r'@app\.route\("/api/ventilacao", methods=\["POST"\]\)',
    r'@app\.route\("/api/aquecedor", methods=\["POST"\]\)',
    r'@app\.route\("/api/modo_automatico", methods=\["POST"\]\)'
]

for route_pattern in routes_to_protect_with_admin:
    if '@require_auth' not in code:
        code = re.sub(
            route_pattern,
            lambda m: "@require_auth(roles=['admin', 'operator'])\n" + m.group(0),
            code
        )

with open('c:/nic/ChikGuard-Original/backend/app.py', 'w', encoding='utf-8') as f:
    f.write(code)
