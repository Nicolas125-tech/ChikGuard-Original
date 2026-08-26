import os
import jwt
import logging
import httpx
from jwt.algorithms import ECAlgorithm
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from supabase import Client, create_client

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET")

if not SUPABASE_JWT_SECRET and not os.environ.get("TESTING"):
    raise RuntimeError("SUPABASE_JWT_SECRET environment variable is required for secure authentication.")

if SUPABASE_URL and SUPABASE_KEY and not os.environ.get("TESTING"):
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase_client = None

# Cache da chave pública JWKS do Supabase (ES256)
_jwks_cache: dict | None = None

def _get_supabase_public_key(token: str):
    """Obtém a chave pública do Supabase via JWKS para validar tokens ES256."""
    global _jwks_cache
    try:
        if _jwks_cache is None:
            jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
            resp = httpx.get(jwks_url, timeout=5)
            resp.raise_for_status()
            _jwks_cache = resp.json()

        # Descobre qual kid o token usa
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        for key_data in _jwks_cache.get("keys", []):
            if key_data.get("kid") == kid:
                return ECAlgorithm.from_jwk(key_data)
    except Exception as e:
        logger.warning(f"Falha ao obter JWKS: {e}")
    return None


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

    decoded = None
    try:
        # Tenta ES256 primeiro (novo padrão Supabase desde 2024)
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        if alg == "ES256":
            public_key = _get_supabase_public_key(token)
            if public_key:
                decoded = jwt.decode(
                    token, public_key,
                    algorithms=["ES256"],
                    audience="authenticated",
                    options={"verify_signature": True}
                )

        # Fallback para HS256 (projetos mais antigos)
        jwt_secret = os.environ.get("SUPABASE_JWT_SECRET") or SUPABASE_JWT_SECRET
        if not jwt_secret:
            raise RuntimeError("SUPABASE_JWT_SECRET environment variable is required for secure authentication.")
        if decoded is None and jwt_secret and alg == "HS256":
            decoded = jwt.decode(
                token, jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_signature": True}
            )

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception as e:
        logger.error(f"Erro de autenticacao FastAPI: {str(e)}")
        raise HTTPException(status_code=401, detail="Erro de processamento de token")

    if decoded is None:
        raise HTTPException(status_code=401, detail="Não foi possível validar o token")

    user_id = decoded.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Busca role e status reais da tabela profiles via service role (bypassa RLS)
    if supabase_client:
        try:
            from fastapi.concurrency import run_in_threadpool
            
            def _get_profile():
                return (
                    supabase_client.table("profiles")
                    .select("role, status, tenant_id")
                    .eq("id", user_id)
                    .single()
                    .execute()
                )

            response = await run_in_threadpool(_get_profile)
            profile = response.data

            if not profile:
                raise HTTPException(status_code=403, detail="Profile not found")
            if profile.get("status") == "PENDING":
                raise HTTPException(status_code=403, detail="Sua conta foi criada, mas aguarda a aprovação de um administrador da granja.")
            if profile.get("status") in ("SUSPENDED", "REJECTED"):
                raise HTTPException(status_code=403, detail="User access denied")

            user_role = profile.get("role", "viewer").lower()
            tenant_id = profile.get("tenant_id") or 1
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao buscar profile: {e}")
            raise HTTPException(status_code=500, detail="Erro ao verificar perfil")
    else:
        user_role = decoded.get("app_metadata", {}).get("role", "viewer").lower()
        tenant_id = decoded.get("app_metadata", {}).get("tenant_id", 1)

    return UserContext(user_id=user_id, role=user_role, tenant_id=tenant_id)


def RequireRole(allowed_roles: list[str]):
    """Dependencia para verificar se o usuario tem as roles necessarias."""
    def role_checker(user: UserContext = Security(get_current_user)):
        if user.role in ("admin", "superadmin"):
            return user
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {allowed_roles}"
            )
        return user
    return role_checker
