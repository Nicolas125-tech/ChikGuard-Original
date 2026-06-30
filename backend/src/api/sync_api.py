from flask import Blueprint, jsonify

from src.security.auth import require_auth


def create_sync_blueprint(deps):
    bp = Blueprint("sync_api", __name__)
    db = deps.get("db")
    SyncQueueItem = deps.get("SyncQueueItem")

    @bp.route("/api/sync/status", methods=["GET"])
    @require_auth()
    def sync_status():
        if not db or not SyncQueueItem:
            return jsonify({"status": "offline", "pending_items": 0}), 200

        try:
            pending = SyncQueueItem.query.filter_by(synced=False).count()
            return jsonify({"status": "online", "pending_items": pending})
        except Exception as e:
            import logging

            logging.getLogger(__name__).error("Erro na API de sync: %s", str(e))
            return jsonify(
                {"status": "error", "message": "Ocorreu um erro interno de sincronizacao."}
            ), 500

    @bp.route("/api/sync/pending", methods=["GET"])
    @require_auth()
    def get_pending_sync():
        return jsonify({"pending": 0}), 200

    @bp.route("/api/sync/ack", methods=["POST"])
    @require_auth()
    def ack_sync():
        return jsonify({"status": "acknowledged"}), 200

    return bp
