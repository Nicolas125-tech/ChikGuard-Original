from flask import Blueprint, jsonify, request

def create_sync_blueprint(deps):
    bp = Blueprint('sync_api', __name__)
    db = deps.get("db")
    SyncQueueItem = deps.get("SyncQueueItem")

    @bp.route("/api/sync/status", methods=["GET"])
    def sync_status():
        if not db or not SyncQueueItem:
            return jsonify({"status": "offline", "pending_items": 0}), 200

        try:
            pending = SyncQueueItem.query.filter_by(synced=False).count()
            return jsonify({"status": "online", "pending_items": pending})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/sync/pending", methods=["GET"])
    def get_pending_sync():
        return jsonify({"pending": 0}), 200

    @bp.route("/api/sync/ack", methods=["POST"])
    def ack_sync():
        return jsonify({"status": "acknowledged"}), 200

    return bp
