import os
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from supabase import Client, create_client
import logging

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "default_secret_for_local_dev")

if SUPABASE_URL and SUPABASE_KEY:
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase_client = None

class UserContext(BaseModel):
    user_id: str
    role: str
    tenant_id: int

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserContext:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token"
        )
    
    try:
        # Validate JWT
        decoded = jwt.decode(
            token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated"
        )

        user_id = decoded.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        if supabase_client:
            response = (
                supabase_client.table("profiles")
                .select("role, status, tenant_id")
                .eq("id", user_id)
                .single()
                .execute()
            )
            profile = response.data
            if not profile:
                raise HTTPException(status_code=403, detail="Profile not found")
            if profile.get("status") == "PENDING":
                raise HTTPException(status_code=403, detail="User awaiting approval")

            user_role = profile.get("role", "viewer").lower()
            tenant_id = profile.get("tenant_id", 1)
        else:
            # Fallback
            user_role = decoded.get("app_metadata", {}).get("role", "viewer").lower()
            tenant_id = decoded.get("app_metadata", {}).get("tenant_id", 1)

        return UserContext(user_id=user_id, role=user_role, tenant_id=tenant_id)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception as e:
        logging.getLogger(__name__).error(f"Erro de autenticacao FastAPI: {str(e)}")
        raise HTTPException(status_code=401, detail="Erro de processamento de token")

def RequireRole(allowed_roles: list[str]):
    """Dependencia para verificar se o usuario tem as roles necessarias."""
    def role_checker(user: UserContext = Security(get_current_user)):
        if "admin" in user.role or "superadmin" in user.role:
            return user
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {allowed_roles}"
            )
        return user
    return role_checker
