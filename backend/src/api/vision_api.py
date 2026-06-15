import os
import time
from datetime import datetime
from io import BytesIO

import numpy as np
from flask import Blueprint, jsonify, request, send_file

from src.security.auth import require_auth


def create_vision_blueprint(deps):
    bp = Blueprint("vision_api", __name__)

    _utcnow = deps.get("utcnow")
    _perf_metrics = deps.get("perf_metrics")
    _camera_capture = deps.get("camera_capture")
    _CV_ENGINE_AVAILABLE = deps.get("CV_ENGINE_AVAILABLE")
    species_counts = deps.get("species_counts")
    BIRD_CLASS_NAME = deps.get("BIRD_CLASS_NAME")
    DETECTION_CONF = deps.get("DETECTION_CONF")
    INFERENCE_IMGSZ = deps.get("INFERENCE_IMGSZ")
    TRACKER_CONFIG = deps.get("TRACKER_CONFIG")
    behavior_state = deps.get("behavior_state")
    immobility_state = deps.get("immobility_state")
    carcass_state = deps.get("carcass_state")
    _heatmap_grid = deps.get("heatmap_grid")
    _heatmap_grid_last_hours = deps.get("heatmap_grid_last_hours")
    _heatmap_points_3d = deps.get("heatmap_points_3d")
    _heatmap_image_bytes = deps.get("heatmap_image_bytes")
    HEATMAP_DIR = deps.get("HEATMAP_DIR")
    tamper_state = deps.get("tamper_state")
    sensor_state = deps.get("sensor_state")
    TAMPER_SENSOR_STALE_SEC = deps.get("TAMPER_SENSOR_STALE_SEC")
    ACTIVE_CAMERA_ID = deps.get("active_camera_id")

    @bp.route("/api/vision/metrics", methods=["GET"])
    @require_auth()
    def get_vision_metrics():
        """
        Métricas de performance do pipeline de visão computacional em tempo real.
        Retorna FPS da câmera, FPS da inferência YOLO, latência em ms e contagem por espécie.
        """
        metrics = (
            _perf_metrics.get()
            if _perf_metrics
            else {"fps_camera": 0.0, "fps_inference": 0.0, "latency_ms": 0.0}
        )
        camera_live = (
            bool(_camera_capture and _camera_capture.is_live) if _camera_capture else False
        )
        return jsonify(
            {
                "cv_engine_active": bool(_CV_ENGINE_AVAILABLE),
                "camera_live": camera_live,
                "fps_camera": metrics.get("fps_camera", 0.0),
                "fps_inference": metrics.get("fps_inference", 0.0),
                "latency_ms": metrics.get("latency_ms", 0.0),
                "species_counts": species_counts,
                "bird_class_name": BIRD_CLASS_NAME,
                "detection_conf": DETECTION_CONF,
                "inference_imgsz": INFERENCE_IMGSZ,
                "tracker": TRACKER_CONFIG,
            }
        )

    @bp.route("/api/behavior/live", methods=["GET"])
    @require_auth()
    def get_behavior_live():
        return jsonify(
            {
                "status": behavior_state["status"],
                "message": behavior_state["message"],
                "dispersion_ratio": behavior_state["dispersion_ratio"],
                "edge_ratio": behavior_state["edge_ratio"],
                "count": behavior_state["count"],
                "updated_at_epoch": behavior_state["updated_at"],
            }
        )

    @bp.route("/api/immobility/live", methods=["GET"])
    @require_auth()
    def get_immobility_live():
        now = time.time()
        items = []
        for uid, state in immobility_state.items():
            ax, ay = state["anchor"]
            items.append(
                {
                    "bird_uid": int(uid),
                    "x": int(ax),
                    "y": int(ay),
                    "immobile_seconds": round(max(0.0, now - float(state["since"])), 1),
                    "alerted": bool(state.get("alerted", False)),
                }
            )
        items.sort(key=lambda x: x["immobile_seconds"], reverse=True)
        return jsonify({"count": len(items), "items": items[:200]})

    @bp.route("/api/carcass/live", methods=["GET"])
    @require_auth()
    def carcass_live():
        items = carcass_state.get("items", [])
        return jsonify(
            {
                "count": len(items),
                "audio_alert": len(items) > 0,
                "message": "Atencao: Possivel ave morta no setor X"
                if items
                else "Sem carcacas detectadas",
                "items": items,
            }
        )

    @bp.route("/api/heatmap/daily", methods=["GET"])
    @require_auth()
    def get_daily_heatmap():
        date_str = request.args.get("date")
        grid_size = request.args.get("grid", default=32, type=int)
        grid_size = max(8, min(grid_size, 128))
        try:
            date_ref = (
                datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else _utcnow().date()
            )
        except Exception:
            return jsonify({"msg": "Formato de data invalido. Use YYYY-MM-DD"}), 400

        heat = _heatmap_grid(date_ref=date_ref, grid_size=grid_size)
        total = float(np.sum(heat))
        max_cell = float(np.max(heat))
        norm = (heat / max_cell).tolist() if max_cell > 0 else heat.tolist()
        return jsonify(
            {
                "date": date_ref.strftime("%Y-%m-%d"),
                "grid_size": grid_size,
                "total_points": int(total),
                "max_cell": max_cell,
                "matrix": norm,
            }
        )

    @bp.route("/api/heatmap/daily/image", methods=["GET"])
    @require_auth()
    def get_daily_heatmap_image():
        date_str = request.args.get("date")
        try:
            date_ref = (
                datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else _utcnow().date()
            )
        except Exception:
            return jsonify({"msg": "Formato de data invalido. Use YYYY-MM-DD"}), 400

        heat = _heatmap_grid(date_ref=date_ref, grid_size=40)
        img_bytes = _heatmap_image_bytes(heat)
        if img_bytes is None:
            return jsonify({"msg": "Falha ao gerar imagem de heatmap"}), 500

        file_name = f"heatmap_{ACTIVE_CAMERA_ID}_{date_ref.strftime('%Y%m%d')}.jpg"
        save_path = os.path.join(HEATMAP_DIR, file_name)
        with open(save_path, "wb") as f:
            f.write(img_bytes)
        return send_file(
            BytesIO(img_bytes), mimetype="image/jpeg", as_attachment=False, download_name=file_name
        )

    @bp.route("/api/heatmap/rolling24", methods=["GET"])
    @require_auth()
    def get_rolling24_heatmap():
        hours = request.args.get("hours", default=24, type=int)
        grid_size = request.args.get("grid", default=40, type=int)
        grid_size = max(8, min(grid_size, 128))
        heat = _heatmap_grid_last_hours(hours=hours, grid_size=grid_size)
        total = float(np.sum(heat))
        max_cell = float(np.max(heat))
        norm = (heat / max_cell).tolist() if max_cell > 0 else heat.tolist()
        return jsonify(
            {"hours": hours, "grid_size": grid_size, "total_points": int(total), "matrix": norm}
        )

    @bp.route("/api/heatmap/rolling24/image", methods=["GET"])
    @require_auth()
    def get_rolling24_heatmap_image():
        hours = request.args.get("hours", default=24, type=int)
        heat = _heatmap_grid_last_hours(hours=hours, grid_size=40)
        img_bytes = _heatmap_image_bytes(heat)
        if img_bytes is None:
            return jsonify({"msg": "Falha ao gerar heatmap rolling"}), 500
        return send_file(
            BytesIO(img_bytes),
            mimetype="image/jpeg",
            as_attachment=False,
            download_name="heatmap_rolling24.jpg",
        )

    @bp.route("/api/heatmap/3d", methods=["GET"])
    @require_auth()
    def get_heatmap_3d():
        hours = request.args.get("hours", default=24, type=int)
        grid_size = request.args.get("grid", default=24, type=int)
        grid_size = max(8, min(grid_size, 64))
        points = _heatmap_points_3d(hours=hours, grid_size=grid_size)
        return jsonify(
            {
                "camera_id": ACTIVE_CAMERA_ID,
                "hours": max(1, min(hours, 168)),
                "grid_size": grid_size,
                "points_count": len(points),
                "points": points,
            }
        )

    @bp.route("/api/security/tamper", methods=["GET"])
    @require_auth()
    def tamper_status():
        age = time.time() - float(sensor_state.get("updated_at", 0.0))
        return jsonify(
            {
                "camera_id": ACTIVE_CAMERA_ID,
                "last_alert_ts": float(tamper_state.get("last_alert_ts", 0.0)),
                "last_causes": tamper_state.get("last_causes", []),
                "alerts_count": int(tamper_state.get("alerts_count", 0)),
                "dark_frames": int(tamper_state.get("dark_frames", 0)),
                "freeze_frames": int(tamper_state.get("freeze_frames", 0)),
                "sensor_stale": bool(age > TAMPER_SENSOR_STALE_SEC),
                "sensor_age_sec": round(float(age), 2),
            }
        )

    return bp
