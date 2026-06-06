import os
import jwt
from functools import wraps
from flask import request, jsonify
from supabase import create_client, Client

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '') # Service role key ideally, or anon key if RLS allows
SUPABASE_JWT_SECRET = os.environ.get('SUPABASE_JWT_SECRET')

if not SUPABASE_JWT_SECRET:
    raise RuntimeError("SUPABASE_JWT_SECRET environment variable is required for secure authentication.")

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
                    response = supabase_client.table('profiles').select('role, status, tenant_id').eq('id', user_id).single().execute()
                    profile = response.data
                    if not profile:
                        return jsonify({'error': 'Profile not found'}), 403
                    if profile.get('status') == 'PENDING':
                        return jsonify({'error': 'User awaiting approval'}), 403
                        
                    user_role = profile.get('role', 'viewer').lower()
                    tenant_id = profile.get('tenant_id', 1)
                else:
                    # Fallback if supabase client is not configured
                    user_role = decoded.get('app_metadata', {}).get('role', 'viewer').lower()
                    tenant_id = decoded.get('app_metadata', {}).get('tenant_id', 1)

                if roles and user_role not in roles and 'admin' not in user_role and 'superadmin' not in user_role:
                    return jsonify({'error': f'Insufficient permissions. Required: {roles}'}), 403
                    
                request.user_id = user_id
                request.user_role = user_role
                request.tenant_id = tenant_id
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token expired'}), 401
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Erro de autenticacao: {str(e)} - Token: {token[:15]}...")
                print(f"JWT ERROR: {str(e)}")
                return jsonify({'error': 'Erro de processamento de token', 'details': str(e)}), 401
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
