from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.security.fastapi_auth import get_current_user, UserContext, RequireRole, supabase_client
from pydantic import BaseModel
from typing import Optional, List
import logging
import json

router = APIRouter(prefix="/api", tags=["accounts", "admin"])
logger = logging.getLogger(__name__)

ROLE_LEVELS = {"viewer": 1, "operator": 2, "admin": 3, "superadmin": 4}

class UserUpdate(BaseModel):
    role: Optional[str] = None
    active: Optional[bool] = None

class ApproveUserRequest(BaseModel):
    target_user_id: str
    target_role: Optional[str] = "VIEWER"

def write_audit_log(db: Session, actor: str, action: str, details: dict):
    from database import AuditLog
    try:
        row = AuditLog(
            actor=actor,
            action=action,
            source="security",
            details_json=json.dumps(details, ensure_ascii=False)
        )
        db.add(row)
        db.commit()
    except Exception as e:
        logger.error("Failed to write audit log: %s", str(e))

@router.get("/accounts/me")
async def accounts_me(user: UserContext = Depends(get_current_user)):
    if supabase_client:
        try:
            response = supabase_client.table("profiles").select("*").eq("id", user.user_id).single().execute()
            if response.data:
                return response.data
        except Exception as e:
            logger.error("Error fetching profiles: %s", str(e))
    return {"id": user.user_id, "role": user.role, "active": True}

@router.get("/accounts/users")
async def accounts_users(user: UserContext = Depends(RequireRole(["admin", "superadmin"]))):
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Supabase não configurado")
    try:
        response = supabase_client.table("profiles").select("*").execute()
        return {"count": len(response.data or []), "items": response.data or []}
    except Exception as e:
        logger.error("Error fetching users: %s", str(e))
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.patch("/accounts/users/{account_id}")
async def accounts_user_update(
    account_id: str,
    data: UserUpdate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(RequireRole(["admin", "superadmin"]))
):
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Supabase não configurado")

    current_user_role = user.role.lower()
    current_level = ROLE_LEVELS.get(current_user_role, 0)

    try:
        profile_response = supabase_client.table("profiles").select("role").eq("id", account_id).single().execute()
        if not profile_response.data:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        target_user_role = str(profile_response.data.get("role", "viewer")).lower()
        target_level = ROLE_LEVELS.get(target_user_role, 0)
    except Exception:
        raise HTTPException(status_code=404, detail="Usuário não encontrado ou erro de acesso")

    if current_level <= target_level and current_user_role != "superadmin":
        raise HTTPException(status_code=403, detail="Não é possível modificar usuários com nível igual ou superior")

    try:
        update_data = {}
        if data.role is not None:
            role = data.role.strip().lower()
            if role in ROLE_LEVELS:
                new_role_level = ROLE_LEVELS.get(role, 0)
                if new_role_level >= current_level and current_user_role != "superadmin":
                    raise HTTPException(status_code=403, detail="Não é possível atribuir um nível igual ou superior ao seu")
                update_data["role"] = role
        if data.active is not None:
            update_data["status"] = "ACTIVE" if data.active else "SUSPENDED"

        if update_data:
            supabase_client.table("profiles").update(update_data).eq("id", account_id).execute()

        write_audit_log(db, user.user_id, "account_updated_supabase", {"account_id": account_id, "payload_keys": list(update_data.keys())})
        return {"msg": "Conta atualizada via Supabase"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating user: %s", str(e))
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.delete("/accounts/users/{account_id}")
async def accounts_user_delete(
    account_id: str,
    db: Session = Depends(get_db),
    user: UserContext = Depends(RequireRole(["admin", "superadmin"]))
):
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Supabase não configurado")

    current_user_role = user.role.lower()
    current_level = ROLE_LEVELS.get(current_user_role, 0)

    try:
        profile_response = supabase_client.table("profiles").select("role").eq("id", account_id).single().execute()
        if not profile_response.data:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        target_user_role = str(profile_response.data.get("role", "viewer")).lower()
        target_level = ROLE_LEVELS.get(target_user_role, 0)
    except Exception:
        raise HTTPException(status_code=404, detail="Usuário não encontrado ou erro de acesso")

    if current_level <= target_level and current_user_role != "superadmin":
        raise HTTPException(status_code=403, detail="Não é possível excluir usuários com nível igual ou superior")

    try:
        supabase_client.auth.admin.delete_user(account_id)
        write_audit_log(db, user.user_id, "account_deleted_supabase", {"account_id": account_id})
        return {"msg": "Conta excluida com sucesso do Supabase Auth"}
    except Exception as e:
        logger.error("Error deleting user: %s", str(e))
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.get("/admin/pending-users")
async def admin_pending_users(user: UserContext = Depends(RequireRole(["admin", "superadmin"]))):
    if not supabase_client:
        raise HTTPException(status_code=500, detail="Supabase não configurado")
    try:
        response = supabase_client.table("profiles").select("*").eq("status", "PENDING").execute()
        return {"items": response.data or []}
    except Exception as e:
        logger.error("Error fetching pending users: %s", str(e))
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@router.post("/admin/approve-user")
async def admin_approve_user(
    data: ApproveUserRequest,
    db: Session = Depends(get_db),
    user: UserContext = Depends(RequireRole(["admin", "superadmin"]))
):
    current_user_role = user.role.lower()
    current_level = ROLE_LEVELS.get(current_user_role, 0)
    target_role_lower = data.target_role.lower()
    target_role_level = ROLE_LEVELS.get(target_role_lower, 0)

    if target_role_level >= current_level and current_user_role != "superadmin":
        raise HTTPException(status_code=403, detail="Não é possível aprovar um usuário com nível igual ou superior ao seu")

    if not supabase_client:
        raise HTTPException(status_code=500, detail="Supabase não configurado")

    try:
        response = (
            supabase_client.table("profiles")
            .update({"status": "ACTIVE", "role": data.target_role.upper(), "approved_at": "now()"})
            .eq("id", data.target_user_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=400, detail="Falha ao atualizar no Supabase")

        write_audit_log(db, user.user_id, "iam_user_approved", {"target_user_id": data.target_user_id, "role": data.target_role})
        return {"message": "User approved successfully", "data": response.data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error approving user: %s", str(e))
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
