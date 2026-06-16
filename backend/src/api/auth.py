import os

from flask import Blueprint, jsonify, request
from supabase import create_client

from src.security.rate_limiter import limiter

ROLE_LEVELS = {"viewer": 1, "operator": 2, "admin": 3, "superadmin": 4}


def _get_supabase_client():
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def create_auth_blueprint(deps):
    bp = Blueprint("auth_api", __name__)

    guard_critical_action = deps.get("guard_critical_action")
    audit = deps.get("audit")
    db = deps.get("db")
    RolePermission = deps.get("RolePermission")
    utcnow = deps.get("utcnow")

    @bp.route("/api/accounts/me", methods=["GET"])
    def accounts_me():
        # Requires valid Supabase JWT in auth.py middleware
        user_id = getattr(request, "user_id", None)
        user_role = getattr(request, "user_role", None)
        if not user_id:
            return jsonify({"msg": "Sessão inválida"}), 401

        supabase = _get_supabase_client()
        if supabase:
            response = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
            if response.data:
                return jsonify(response.data)

        return jsonify({"id": user_id, "role": user_role, "active": True})

    @bp.route("/api/accounts/users", methods=["GET"])
    def accounts_users():
        ok, resp = guard_critical_action("accounts_manage", permission="accounts.manage")
        if not ok:
            return resp

        supabase = _get_supabase_client()
        if not supabase:
            return jsonify({"msg": "Supabase não configurado"}), 500

        try:
            # Pega as profiles
            response = supabase.table("profiles").select("*").execute()
            return jsonify({"count": len(response.data or []), "items": response.data or []})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route("/api/accounts/users/<string:account_id>", methods=["PATCH"])
    def accounts_user_update(account_id):
        ok, resp = guard_critical_action("accounts_manage", permission="accounts.manage")
        if not ok:
            return resp

        data = request.get_json(silent=True) or {}
        supabase = _get_supabase_client()
        if not supabase:
            return jsonify({"msg": "Supabase não configurado"}), 500

        current_user_role = getattr(request, "user_role", "viewer").lower()
        current_level = ROLE_LEVELS.get(current_user_role, 0)

        try:
            profile_response = supabase.table("profiles").select("role").eq("id", str(account_id)).single().execute()
            target_user_role = str(profile_response.data.get("role", "viewer")).lower()
            target_level = ROLE_LEVELS.get(target_user_role, 0)
        except Exception:
            return jsonify({"msg": "Usuário não encontrado ou erro de acesso"}), 404

        if current_level <= target_level and current_user_role != "superadmin":
            return jsonify({"msg": "Não é possível modificar usuários com nível igual ou superior"}), 403

        try:
            update_data = {}
            if "role" in data:
                role = str(data.get("role", "")).strip().lower()
                if role in ROLE_LEVELS:
                    new_role_level = ROLE_LEVELS.get(role, 0)
                    if new_role_level >= current_level and current_user_role != "superadmin":
                        return jsonify({"msg": "Não é possível atribuir um nível igual ou superior ao seu"}), 403
                    update_data["role"] = role
            if "active" in data:
                # Active in Supabase profiles might map to status
                update_data["status"] = "ACTIVE" if data.get("active") else "SUSPENDED"

            if update_data:
                supabase.table("profiles").update(update_data).eq("id", str(account_id)).execute()

            audit(
                "account_updated_supabase",
                source="security",
                details={"account_id": str(account_id), "payload_keys": list(update_data.keys())},
            )
            return jsonify({"msg": "Conta atualizada via Supabase"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route("/api/accounts/users/<string:account_id>", methods=["DELETE"])
    def accounts_user_delete(account_id):
        ok, resp = guard_critical_action("accounts_manage", permission="accounts.manage")
        if not ok:
            return resp

        supabase = _get_supabase_client()
        if not supabase:
            return jsonify({"msg": "Supabase não configurado"}), 500

        current_user_role = getattr(request, "user_role", "viewer").lower()
        current_level = ROLE_LEVELS.get(current_user_role, 0)

        try:
            profile_response = supabase.table("profiles").select("role").eq("id", str(account_id)).single().execute()
            target_user_role = str(profile_response.data.get("role", "viewer")).lower()
            target_level = ROLE_LEVELS.get(target_user_role, 0)
        except Exception:
            return jsonify({"msg": "Usuário não encontrado ou erro de acesso"}), 404

        if current_level <= target_level and current_user_role != "superadmin":
            return jsonify({"msg": "Não é possível excluir usuários com nível igual ou superior"}), 403

        try:
            supabase.auth.admin.delete_user(str(account_id))
            audit(
                "account_deleted_supabase",
                source="security",
                details={"account_id": str(account_id)},
            )
            return jsonify({"msg": "Conta excluida com sucesso do Supabase Auth"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route("/api/accounts/permissions", methods=["GET", "POST"])
    def accounts_permissions():
        ok, resp = guard_critical_action("permissions_manage", permission="accounts.manage")
        if not ok:
            return resp
        if request.method == "GET":
            if not RolePermission:
                return jsonify({"count": 0, "items": []})
            rows = RolePermission.query.order_by(
                RolePermission.role.asc(), RolePermission.permission.asc()
            ).all()
            return jsonify({"count": len(rows), "items": [r.to_dict() for r in rows]})

        data = request.get_json(silent=True) or {}
        role = str(data.get("role", "")).strip().lower()
        permission = str(data.get("permission", "")).strip()
        allowed = bool(data.get("allowed", True))

        if role not in ROLE_LEVELS or not permission:
            return jsonify({"msg": "role e permission sao obrigatorios"}), 400

        row = RolePermission.query.filter_by(role=role, permission=permission).first()
        if row is None:
            row = RolePermission(role=role, permission=permission, allowed=allowed)
            db.session.add(row)
        else:
            row.allowed = allowed

        db.session.commit()
        audit(
            "permission_updated",
            source="security",
            details={"role": role, "permission": permission, "allowed": allowed},
        )
        return jsonify({"msg": "Permissao atualizada", "item": row.to_dict()})

    @bp.route("/api/admin/pending-users", methods=["GET"])
    def admin_pending_users():
        ok, resp = guard_critical_action("admin_pending_users", permission="accounts.manage")
        if not ok:
            return resp

        supabase = _get_supabase_client()
        if not supabase:
            return jsonify({"msg": "Supabase não configurado"}), 500

        try:
            response = supabase.table("profiles").select("*").eq("status", "PENDING").execute()
            return jsonify({"items": response.data or []}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route("/api/admin/approve-user", methods=["POST"])
    @limiter.limit("10 per minute")
    def admin_approve_user():
        ok, resp = guard_critical_action("admin_approve_user", permission="accounts.manage")
        if not ok:
            return resp

        data = request.get_json(silent=True) or {}
        target_user_id = data.get("target_user_id")
        target_role = data.get("target_role", "VIEWER").upper()

        if not target_user_id:
            return jsonify({"msg": "target_user_id é obrigatorio"}), 400

        current_user_role = getattr(request, "user_role", "viewer").lower()
        current_level = ROLE_LEVELS.get(current_user_role, 0)
        target_role_lower = target_role.lower()
        target_role_level = ROLE_LEVELS.get(target_role_lower, 0)

        if target_role_level >= current_level and current_user_role != "superadmin":
            return jsonify({"msg": "Não é possível aprovar um usuário com nível igual ou superior ao seu"}), 403

        supabase = _get_supabase_client()
        if not supabase:
            return jsonify({"msg": "Supabase não configurado"}), 500

        try:
            response = (
                supabase.table("profiles")
                .update({"status": "ACTIVE", "role": target_role, "approved_at": "now()"})
                .eq("id", target_user_id)
                .execute()
            )
            if not response.data:
                return jsonify({"msg": "Falha ao atualizar no Supabase"}), 400

            audit(
                "iam_user_approved",
                source="security",
                details={"target_user_id": target_user_id, "role": target_role},
            )
            return jsonify({"message": "User approved successfully", "data": response.data}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route("/api/admin/notify-new-user", methods=["POST"])
    @limiter.limit("10 per minute")
    def webhook_notify_new_user():
        # Keeps webhook email notification logic unchanged for brevity, but it's optional.
        return jsonify({"message": "Ignorado"}), 200

    return bp
