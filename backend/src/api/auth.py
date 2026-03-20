from flask import Blueprint, jsonify, request

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
            rows = Account.query.order_by(Account.id.asc()).all()
            return jsonify({"count": len(rows), "items": [r.to_dict() for r in rows]})

        data = request.get_json(silent=True) or {}
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", "")).strip()
        role = str(data.get("role", "operator")).strip().lower()
        active = bool(data.get("active", True))

        if not username or not password:
            return jsonify({"msg": "username e password sao obrigatorios"}), 400
        if role not in ("admin", "operator", "viewer"):
            return jsonify({"msg": "role invalido"}), 400
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
        audit("account_created", source="security", details={"username": username, "role": role, "active": active})
        return jsonify({"msg": "Conta criada", "item": row.to_dict()}), 201

    @bp.route("/api/accounts/users/<int:account_id>", methods=["PATCH"])
    def accounts_user_update(account_id):
        ok, resp = guard_critical_action("accounts_manage", permission="accounts.manage")
        if not ok:
            return resp
        row = Account.query.get(account_id)
        if row is None:
            return jsonify({"msg": "Conta nao encontrada"}), 404

        data = request.get_json(silent=True) or {}
        if "role" in data:
            role = str(data.get("role", "")).strip().lower()
            if role not in ("admin", "operator", "viewer"):
                return jsonify({"msg": "role invalido"}), 400
            row.role = role
        if "active" in data:
            row.active = bool(data.get("active"))
        if "password" in data:
            pwd = str(data.get("password", "")).strip()
            if len(pwd) < 6:
                return jsonify({"msg": "password muito curto (min 6)"}), 400
            row.password_hash = bcrypt.generate_password_hash(pwd).decode("utf-8")

        db.session.commit()
        audit("account_updated", source="security", details={"account_id": account_id, "payload_keys": list(data.keys())})
        return jsonify({"msg": "Conta atualizada", "item": row.to_dict()})

    @bp.route("/api/accounts/permissions", methods=["GET", "POST"])
    def accounts_permissions():
        ok, resp = guard_critical_action("permissions_manage", permission="accounts.manage")
        if not ok:
            return resp
        if request.method == "GET":
            rows = RolePermission.query.order_by(RolePermission.role.asc(), RolePermission.permission.asc()).all()
            return jsonify({"count": len(rows), "items": [r.to_dict() for r in rows]})

        data = request.get_json(silent=True) or {}
        role = str(data.get("role", "")).strip().lower()
        permission = str(data.get("permission", "")).strip()
        allowed = bool(data.get("allowed", True))

        if role not in ("admin", "operator", "viewer") or not permission:
            return jsonify({"msg": "role e permission sao obrigatorios"}), 400

        row = RolePermission.query.filter_by(role=role, permission=permission).first()
        if row is None:
            row = RolePermission(role=role, permission=permission, allowed=allowed)
            db.session.add(row)
        else:
            row.allowed = allowed

        db.session.commit()
        audit("permission_updated", source="security", details={"role": role, "permission": permission, "allowed": allowed})
        return jsonify({"msg": "Permissao atualizada", "item": row.to_dict()})

    return bp
