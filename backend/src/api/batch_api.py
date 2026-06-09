from flask import Blueprint, jsonify, request
from database import db, Batch, BatchLogbook
from datetime import datetime
from src.security.auth import require_auth
from flask_jwt_extended import get_jwt_identity


def create_batch_blueprint(deps):
    bp = Blueprint("batch", __name__, url_prefix="/api/batches")
    _audit = deps.get("audit_fn")
    _guard = deps.get("guard_critical_action")
    _utcnow = deps.get("utcnow_fn", datetime.utcnow)
    _camera_id = deps.get("active_camera_id", "galpao-1")

    @bp.route("", methods=["GET"])
    @require_auth()
    def get_batches():
        batches = (
            Batch.query.filter_by(camera_id=_camera_id).order_by(Batch.start_date.desc()).all()
        )
        return jsonify([b.to_dict() for b in batches])

    @bp.route("/active", methods=["GET"])
    @require_auth()
    def get_active_batch():
        active = Batch.query.filter_by(camera_id=_camera_id, active=True).first()
        if not active:
            return jsonify({"msg": "Nenhum lote ativo no momento"}), 404

        age_days = (_utcnow() - active.start_date).days
        resp = active.to_dict()
        resp["age_days"] = max(0, age_days)
        return jsonify(resp)

    @bp.route("", methods=["POST"])
    @require_auth()
    def start_batch():
        ok, error_resp = _guard("start_batch", permission="batch.manage")
        if not ok:
            return error_resp

        # Encerrar o lote atual caso exista
        active = Batch.query.filter_by(camera_id=_camera_id, active=True).first()
        if active:
            active.active = False

        data = request.get_json() or {}
        name = data.get("name", f"Lote {_utcnow().strftime('%Y-%m')}")
        notes = data.get("notes", "")

        new_batch = Batch(
            camera_id=_camera_id, name=name, active=True, start_date=_utcnow(), notes=notes
        )
        db.session.add(new_batch)
        db.session.commit()

        if _audit:
            _audit("batch_started", details={"name": name})

        return jsonify({"msg": "Lote iniciado com sucesso", "batch": new_batch.to_dict()}), 201

    @bp.route("/close", methods=["POST"])
    @require_auth()
    def close_batch():
        ok, error_resp = _guard("close_batch", permission="batch.manage")
        if not ok:
            return error_resp

        active = Batch.query.filter_by(camera_id=_camera_id, active=True).first()
        if not active:
            return jsonify({"msg": "Nenhum lote ativo para encerrar"}), 404

        active.active = False
        db.session.commit()

        if _audit:
            _audit("batch_closed", details={"id": active.id})

        return jsonify({"msg": "Lote encerrado com sucesso", "batch": active.to_dict()})

    @bp.route("/<int:batch_id>/logbook", methods=["POST"])
    @require_auth()
    def add_logbook(batch_id):
        ok, error_resp = _guard("add_logbook", permission="logbook.write")
        if not ok:
            return error_resp

        data = request.get_json() or {}
        note = data.get("note", "").strip()
        if not note:
            return jsonify({"msg": "Nota é obrigatória"}), 400

        # Tenta pegar quem está logado
        author = "Operador"
        try:
            author = str(get_jwt_identity())
        except:
            pass

        log = BatchLogbook(
            camera_id=_camera_id, batch_id=batch_id, note=note, author=author, timestamp=_utcnow()
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({"msg": "Nota adicionada ao diário do lote", "log": log.to_dict()}), 201

    return bp
