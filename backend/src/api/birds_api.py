import time

from flask import Blueprint, jsonify, request

from database import BirdIdentity, BirdSnapshot, BirdTrackPoint, WeightEstimate
from src.security.auth import require_auth


def create_birds_blueprint(deps):
    bp = Blueprint("birds_api", __name__)

    _utcnow = deps.get("utcnow")
    timedelta = deps.get("timedelta")
    lock = deps.get("lock")
    live_birds = deps.get("live_birds", {})
    species_counts = deps.get("species_counts", {})
    BIRD_LIVE_TTL_SEC = deps.get("BIRD_LIVE_TTL_SEC", 5.0)
    ACTIVE_CAMERA_ID = deps.get("active_camera_id")

    @bp.route("/api/birds/live", methods=["GET"])
    @require_auth()
    def get_live_birds():
        now = time.time()
        with lock:
            items = [
                {
                    "bird_uid": int(bid),
                    "confidence": round(float(data["conf"]), 4),
                    "bbox": data["box"],
                    "track_id": int(data.get("track_id", -1)),
                    "last_seen_seconds": round(now - float(data["last_seen"]), 2),
                    "species": data.get("species", "bird"),
                    "species_label": data.get("species_label", "AVE"),
                }
                for bid, data in live_birds.items()
                if (now - float(data["last_seen"])) <= BIRD_LIVE_TTL_SEC
            ]
        items.sort(key=lambda item: item["bird_uid"])
        return jsonify(
            {
                "count": len(items),
                "ttl_seconds": BIRD_LIVE_TTL_SEC,
                "items": items,
                "species_counts": species_counts,
            }
        )

    @bp.route("/api/birds/history", methods=["GET"])
    @require_auth()
    def get_birds_history():
        limit = request.args.get("limit", default=300, type=int)
        limit = max(1, min(limit, 5000))
        rows = BirdSnapshot.query.order_by(BirdSnapshot.id.desc()).limit(limit).all()
        return jsonify([row.to_dict() for row in reversed(rows)])

    @bp.route("/api/birds/registry", methods=["GET"])
    @require_auth()
    def get_birds_registry():
        limit = request.args.get("limit", default=500, type=int)
        limit = max(1, min(limit, 10000))
        rows = BirdIdentity.query.order_by(BirdIdentity.last_seen.desc()).limit(limit).all()
        return jsonify({"count": len(rows), "items": [row.to_dict() for row in rows]})

    @bp.route("/api/birds/path/<int:bird_uid>", methods=["GET"])
    @require_auth()
    def get_bird_path(bird_uid):
        limit = request.args.get("limit", default=500, type=int)
        limit = max(1, min(limit, 5000))
        rows = (
            BirdTrackPoint.query.filter_by(bird_uid=bird_uid)
            .order_by(BirdTrackPoint.id.desc())
            .limit(limit)
            .all()
        )
        items = [row.to_dict() for row in reversed(rows)]
        return jsonify({"bird_uid": bird_uid, "count": len(items), "items": items})

    return bp


def create_weight_blueprint(deps):
    bp = Blueprint("weight_api", __name__)

    _utcnow = deps.get("utcnow")
    timedelta = deps.get("timedelta")
    weight_state = deps.get("weight_state", {})
    ACTIVE_CAMERA_ID = deps.get("active_camera_id")

    @bp.route("/api/weight/live", methods=["GET"])
    @require_auth()
    def weight_live():
        return jsonify(
            {
                "camera_id": ACTIVE_CAMERA_ID,
                "avg_weight_g": weight_state.get("avg_weight_g", 0),
                "ideal_weight_g": weight_state.get("ideal_weight_g", 0),
                "count": weight_state.get("count", 0),
                "confidence": weight_state.get("confidence", 0.0),
                "updated_at_epoch": weight_state.get("updated_at", 0.0),
            }
        )

    @bp.route("/api/weight/curve", methods=["GET"])
    @require_auth()
    def weight_curve():
        days = request.args.get("days", default=21, type=int)
        days = max(1, min(days, 120))
        start_dt = _utcnow() - timedelta(days=days)
        rows = (
            WeightEstimate.query.filter(
                WeightEstimate.camera_id == ACTIVE_CAMERA_ID, WeightEstimate.timestamp >= start_dt
            )
            .order_by(WeightEstimate.timestamp.asc())
            .all()
        )
        points = [r.to_dict() for r in rows]
        return jsonify({"count": len(points), "items": points})

    return bp
