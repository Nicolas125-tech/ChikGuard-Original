import os
import time
import smtplib
import hmac
from email.message import EmailMessage
from flask import Blueprint, jsonify, request
from supabase import create_client
from src.security.rate_limiter import limiter


ROLE_LEVELS = {"viewer": 1, "operator": 2, "admin": 3, "superadmin": 4}

def create_auth_blueprint(deps):
    bp = Blueprint("auth_api", __name__)

    # dependencies injected from app.py
    guard_critical_action = deps.get("guard_critical_action")
    get_current_account = deps.get("get_current_account")
    audit = deps.get("audit")
    bcrypt = deps.get("bcrypt")
    db = deps.get("db")
    Account = deps.get("Account")
    RolePermission = deps.get("RolePermission")
    create_access_token = deps.get("create_access_token")
    request_ip = deps.get("request_ip")
    utcnow = deps.get("utcnow")
    login_attempt_state = deps.get("login_attempt_state", {})
    LOGIN_RATE_WINDOW_SEC = deps.get("login_rate_window_sec", 300)
    LOGIN_RATE_MAX_ATTEMPTS = deps.get("login_rate_max_attempts", 5)

    @bp.route("/api/accounts/me", methods=["GET"])
    def accounts_me():
        ok, resp = guard_critical_action("accounts_me_view", permission="monitor.read")
        if not ok:
            return resp
        account = get_current_account()
        if account is None:
            return jsonify({"msg": "Conta nao encontrada"}), 404
        return jsonify(account.to_dict())

    @bp.route("/api/accounts/users", methods=["GET", "POST"])
    def accounts_users():
        ok, resp = guard_critical_action("accounts_manage", permission="accounts.manage")
        if not ok:
            return resp
        if request.method == "GET":
            # Try fetching from Supabase first
            try:
                SUPABASE_URL = os.environ.get("SUPABASE_URL")
                SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
                if SUPABASE_URL and SUPABASE_KEY:
                    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                    response = supabase.table("profiles").select("*").execute()
                    if response.data:
                        return jsonify({"count": len(response.data), "items": response.data})
            except Exception as e:
                pass  # fallback to local db
            rows = Account.query.order_by(Account.id.asc()).all()
            return jsonify({"count": len(rows), "items": [r.to_dict() for r in rows]})

        data = request.get_json(silent=True) or {}
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", "")).strip()
        role = str(data.get("role", "operator")).strip().lower()
        active = bool(data.get("active", True))

        if not username or not password:
            return jsonify({"msg": "username e password sao obrigatorios"}), 400
        if len(password) < 8:
            return jsonify({"msg": "password muito curto (min 8 caracteres)"}), 400
        if len(username) > 50 or len(password) > 100:
            return jsonify({"msg": "Tamanho de usuario ou senha excede o limite"}), 400
        if role not in ROLE_LEVELS:
            return jsonify({"msg": "role invalido"}), 400

        account = get_current_account()
        actor_role = account.role if account else "viewer"
        actor_level = ROLE_LEVELS.get(actor_role, 0)
        target_level = ROLE_LEVELS.get(role, 0)

        if target_level > actor_level:
            return jsonify({"msg": "Apenas usuarios com cargo superior podem criar esta conta"}), 403
        if target_level == actor_level and actor_role not in ["superadmin", "admin"]:
            return jsonify({"msg": "Apenas admins e superadmins podem criar contas de mesmo nivel"}), 403

        if Account.query.filter_by(username=username).first() is not None:
            return jsonify({"msg": "usuario ja existe"}), 409

        row = Account(
            username=username,
            password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
            role=role,
            active=active,
        )
        db.session.add(row)
        db.session.commit()
        audit(
            "account_created",
            source="security",
            details={"username": username, "role": role, "active": active},
        )
        return jsonify({"msg": "Conta criada", "item": row.to_dict()}), 201

    @bp.route("/api/accounts/users/<int:account_id>", methods=["PATCH"])
    def accounts_user_update(account_id):
        ok, resp = guard_critical_action("accounts_manage", permission="accounts.manage")
        if not ok:
            return resp
        row = Account.query.get(account_id)
        if row is None:
            return jsonify({"msg": "Conta nao encontrada"}), 404

        account = get_current_account()
        actor_role = account.role if account else "viewer"
        actor_id = account.id if account else None
        actor_level = ROLE_LEVELS.get(actor_role, 0)
        target_current_level = ROLE_LEVELS.get(row.role, 0)

        if target_current_level > actor_level and actor_id != account_id:
            return jsonify({"msg": "Permissao negada para alterar conta com cargo superior"}), 403
        if target_current_level == actor_level and actor_id != account_id and actor_role not in ["superadmin", "admin"]:
            return jsonify({"msg": "Permissao negada para alterar conta com cargo igual"}), 403

        data = request.get_json(silent=True) or {}
        if "role" in data:
            role = str(data.get("role", "")).strip().lower()
            if role != row.role:
                if role not in ROLE_LEVELS:
                    return jsonify({"msg": "role invalido"}), 400
                target_new_level = ROLE_LEVELS.get(role, 0)

                if target_new_level > actor_level:
                    return jsonify({"msg": "Permissao negada para elevar a cargo superior ao seu"}), 403
                if target_new_level == actor_level and actor_role not in ["superadmin", "admin"]:
                    return jsonify({"msg": "Permissao negada para elevar a cargo igual ao seu"}), 403
                row.role = role
        if "active" in data:
            row.active = bool(data.get("active"))
        if "password" in data:
            pwd = str(data.get("password", "")).strip()
            if len(pwd) < 8:
                return jsonify({"msg": "password muito curto (min 8 caracteres)"}), 400
            if len(pwd) > 100:
                return jsonify({"msg": "Tamanho da senha excede o limite"}), 400
            row.password_hash = bcrypt.generate_password_hash(pwd).decode("utf-8")

        db.session.commit()
        audit(
            "account_updated",
            source="security",
            details={"account_id": account_id, "payload_keys": list(data.keys())},
        )
        return jsonify({"msg": "Conta atualizada", "item": row.to_dict()})

    @bp.route("/api/accounts/users/<int:account_id>", methods=["DELETE"])
    def accounts_user_delete(account_id):
        ok, resp = guard_critical_action("accounts_manage", permission="accounts.manage")
        if not ok:
            return resp

        row = Account.query.get(account_id)
        if row is None:
            return jsonify({"msg": "Conta nao encontrada"}), 404

        account = get_current_account()
        actor_role = account.role if account else "viewer"
        actor_level = ROLE_LEVELS.get(actor_role, 0)
        target_level = ROLE_LEVELS.get(row.role, 0)

        if row.role == "superadmin":
            return jsonify({"msg": "Nao é possivel excluir um superadmin localmente"}), 403

        if target_level > actor_level:
            return jsonify({"msg": "Permissao negada para excluir conta com cargo superior"}), 403
        if target_level == actor_level and actor_role not in ["superadmin", "admin"]:
            return jsonify({"msg": "Permissao negada para excluir conta com cargo igual"}), 403

        username = row.username
        is_email = "@" in username

        try:
            db.session.delete(row)
            db.session.commit()
            audit(
                "account_deleted",
                source="security",
                details={"account_id": account_id, "username": username},
            )
        except Exception as e:
            db.session.rollback()
            import logging

            logging.error(f"Erro ao excluir conta local: {e}")
            return jsonify({"error": "Erro interno ao excluir conta local"}), 500

        if is_email:
            try:
                SUPABASE_URL = os.environ.get("SUPABASE_URL")
                SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

                if (
                    SUPABASE_URL
                    and SUPABASE_KEY
                    and SUPABASE_KEY != "YOUR_SUPABASE_SERVICE_ROLE_KEY_HERE"
                ):
                    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

                    try:
                        users_resp = supabase.auth.admin.list_users()
                        for u in users_resp:
                            if u.email == username:
                                supabase.auth.admin.delete_user(u.id)
                                break
                    except Exception as e:
                        import logging

                        logging.getLogger(__name__).error(
                            "Failed to delete user from Supabase auth: %s", e
                        )
            except Exception as e:
                import logging

                logging.getLogger(__name__).error("Supabase connection error during delete: %s", e)

        return jsonify({"msg": "Conta excluida com sucesso"})

    @bp.route("/api/accounts/permissions", methods=["GET", "POST"])
    def accounts_permissions():
        ok, resp = guard_critical_action("permissions_manage", permission="accounts.manage")
        if not ok:
            return resp
        if request.method == "GET":
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
        
        if len(role) > 50 or len(permission) > 100:
            return jsonify({"msg": "Tamanho dos campos excede o limite"}), 400

        account = get_current_account()
        actor_role = account.role if account else "viewer"
        actor_level = ROLE_LEVELS.get(actor_role, 0)
        target_level = ROLE_LEVELS.get(role, 0)

        if target_level > actor_level:
            return jsonify({"msg": "Permissao negada para alterar permissoes de cargo superior"}), 403
        if target_level == actor_level and actor_role not in ["superadmin", "admin"]:
            return jsonify({"msg": "Permissao negada para alterar permissoes de cargo igual"}), 403

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

        try:
            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

            if not SUPABASE_URL or not SUPABASE_KEY:
                return jsonify({"msg": "Supabase credenciais ausentes no backend"}), 500

            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

            # Usamos a service_role key que da bypass ao RLS.
            # Validamos a permissao "accounts.manage" no Flask e listamos
            response = supabase.table("profiles").select("*").eq("status", "PENDING").execute()
            return jsonify({"items": response.data or []}), 200

        except Exception as e:
            import logging

            logging.error(f"Admin pending users error: {e}")
            return jsonify({"error": "Erro interno no servidor"}), 500

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

        target_role_lower = target_role.lower()
        if target_role_lower not in ROLE_LEVELS:
            return jsonify({"msg": "role invalido"}), 400

        account = get_current_account()
        actor_role = account.role if account else "viewer"
        actor_level = ROLE_LEVELS.get(actor_role, 0)
        target_level = ROLE_LEVELS.get(target_role_lower, 0)

        if target_level > actor_level:
            return jsonify({"msg": "Permissao negada para aprovar usuario com cargo superior"}), 403
        if target_level == actor_level and actor_role not in ["superadmin", "admin"]:
            return jsonify({"msg": "Permissao negada para aprovar usuario com cargo igual"}), 403

        from sqlalchemy import text

        try:
            sql = text(
                "UPDATE profiles SET status = 'ACTIVE', role = :r, approved_at = now() "
                "WHERE id = :uid RETURNING id"
            )
            res = db.session.execute(sql, {"r": target_role, "uid": target_user_id}).fetchone()
            db.session.commit()
            if res:
                audit(
                    "iam_user_approved",
                    source="security_db",
                    details={"target_user_id": target_user_id, "role": target_role},
                )
                return jsonify(
                    {"message": "User approved successfully", "data": {"id": target_user_id}}
                ), 200
        except Exception as e:
            db.session.rollback()
            import logging

            logging.getLogger(__name__).error(
                "Direct DB Update Failed (trying Supabase REST Admin): %s", e
            )

        try:
            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

            if (
                not SUPABASE_URL
                or not SUPABASE_KEY
                or SUPABASE_KEY == "YOUR_SUPABASE_SERVICE_ROLE_KEY_HERE"
            ):
                return jsonify(
                    {"msg": "Supabase credenciais REST ausentes e DB direta falhou"}
                ), 500

            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

            # Update direto usando service_role
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
            import logging

            logging.error(f"Admin approve user error: {e}")
            return jsonify({"error": "Erro interno no servidor"}), 500

    @bp.route("/api/admin/notify-new-user", methods=["POST"])
    @limiter.limit("10 per minute")
    def webhook_notify_new_user():
        WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

        auth_header = request.headers.get("Authorization")
        if WEBHOOK_SECRET and (
            not auth_header
            or not hmac.compare_digest(
                auth_header.encode("utf-8"), f"Bearer {WEBHOOK_SECRET}".encode("utf-8")
            )
        ):
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json(silent=True) or {}

        if data.get("type") == "INSERT" and "record" in data:
            new_profile = data["record"]

            if new_profile.get("status") == "PENDING":
                user_id = new_profile.get("id")

                SUPERADMIN_EMAIL = os.environ.get("SUPERADMIN_EMAIL", "admin@chikguard.com")
                SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.sendgrid.net")
                SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
                SMTP_USER = os.environ.get("SMTP_USER")
                SMTP_PASS = os.environ.get("SMTP_PASS")

                msg = EmailMessage()
                msg["Subject"] = "ChikGuard: Nova conta a aguardar aprovação"
                msg["From"] = "noreply@chikguard.com"
                msg["To"] = SUPERADMIN_EMAIL

                msg.set_content(
                    f"Olá SuperAdmin,\n\n"
                    f"Um novo utilizador registou-se no sistema e está a aguardar a sua aprovação.\n\n"
                    f"ID do Utilizador: {user_id}\n\n"
                    f"Por favor, aceda ao Painel Admin do ChikGuard para aprovar ou rejeitar o utilizador."
                )

                try:
                    if SMTP_HOST and SMTP_PORT:
                        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                            server.starttls()
                            if SMTP_USER and SMTP_PASS:
                                server.login(SMTP_USER, SMTP_PASS)
                            server.send_message(msg)
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).error("Erro SMTP webhook: %s", e)

                return jsonify({"message": "Notificação processada"}), 200

        return jsonify({"message": "Ignorado"}), 400

    @bp.route("/api/login", methods=["POST", "OPTIONS"])
    @limiter.limit("5 per minute")
    def login():
        if request.method == "OPTIONS":
            return jsonify({}), 200

        ip = request_ip()
        now_ts = time.time()

        # Rate limit cleanup
        state = login_attempt_state.get(ip, {"count": 0, "first_attempt": now_ts})
        if now_ts - state["first_attempt"] > LOGIN_RATE_WINDOW_SEC:
            state = {"count": 0, "first_attempt": now_ts}
            login_attempt_state[ip] = state

        if state["count"] >= LOGIN_RATE_MAX_ATTEMPTS:
            audit(
                "login_failed_rate_limit", source="security", details={"ip": ip}, actor="anonymous"
            )
            return jsonify({"msg": "Muitas tentativas. Tente mais tarde."}), 429

        data = request.get_json(silent=True) or {}
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", "")).strip()

        if not username or not password:
            return jsonify({"msg": "Usuario e senha obrigatorios"}), 400

        if len(username) > 100 or len(password) > 100:
            return jsonify({"msg": "Tamanho de usuario ou senha excede o limite"}), 400

        account = Account.query.filter_by(username=username).first()

        # Defense in depth: Prevent timing-based user enumeration.
        # We always verify a password hash (either the user's or a dummy one)
        # to ensure the login endpoint takes roughly the same time.
        dummy_hash = "$2b$12$aT1/E4n.XqPzG1aL9m.J.OqU3I.H.U8Ww.A2wQ/p.W/mY4.X2wW82"  # Random valid bcrypt hash
        hash_to_check = account.password_hash if account else dummy_hash

        valid_pwd = bcrypt.check_password_hash(hash_to_check, password)

        if not account or not account.active or not valid_pwd:
            state["count"] += 1
            login_attempt_state[ip] = state
            audit(
                "login_failed",
                source="security",
                details={"username": username, "ip": ip},
                actor=username,
            )
            return jsonify({"msg": "Credenciais invalidas"}), 401

        # Success reset
        if ip in login_attempt_state:
            del login_attempt_state[ip]

        account.last_login_at = utcnow()
        db.session.commit()

        audit("login_success", source="security", details={"ip": ip}, actor=account.username)

        # Verifica o status no Supabase profiles se configurado.
        # REGRA: contas admin/superadmin locais são sempre ACTIVE.
        # Para outros roles, tenta buscar o status real no Supabase (apenas se o
        # username for um e-mail — contas locais como "admin" não existem no Supabase).
        status = "PENDING" if account.role not in ["admin", "superadmin"] else "ACTIVE"

        try:
            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            is_email_login = "@" in account.username
            if SUPABASE_URL and SUPABASE_KEY and is_email_login:
                supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
                resp = supabase_client.rpc(
                    "get_user_status_by_email", {"user_email": account.username}
                ).execute()
                # Só sobrescreve se o Supabase devolver um valor válido e diferente
                # de PENDING para contas privilegiadas (evita regressão)
                supabase_status = resp.data if resp.data else None
                if supabase_status in ("ACTIVE", "SUSPENDED", "PENDING"):
                    # Não regride admin/superadmin para PENDING por problema de sync
                    if account.role in ("admin", "superadmin") and supabase_status == "PENDING":
                        pass  # mantém ACTIVE
                    else:
                        status = supabase_status
        except Exception as e:
            import logging

            logging.getLogger(__name__).error("Supabase sync error (non-critical): %s", e)

        access_token = create_access_token(
            identity=str(account.id),
            additional_claims={
                "role": account.role,
                "username": account.username,
                "status": status,
            },
        )
        return jsonify(
            {
                "access_token": access_token,
                "role": account.role,
                "username": account.username,
                "status": status,
            }
        ), 200

    return bp
