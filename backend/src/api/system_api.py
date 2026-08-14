import time

from flask import Blueprint, jsonify, request

from database import (
    AuditLog,
    BirdIdentity,
    EnergyUsageDaily,
    EventLog,
    Reading,
    SyncQueueItem,
)
from src.api.system_api_extra import add_remaining_routes
from src.security.auth import require_auth

# Cache para evitar count() repetitivo em tabela grande
_cached_total_vistas = None
_cached_total_vistas_time = 0


def _get_temperature_summary(Reading):
    recentes = Reading.query.order_by(Reading.id.desc()).limit(30).all()
    ultima = recentes[0] if recentes else None
    temperaturas = [item.temperatura for item in recentes]
    alertas = [item for item in recentes if item.status != "NORMAL"]

    return {
        "temperatura_atual": ultima.temperatura if ultima else 0,
        "status_atual": ultima.status if ultima else "INICIANDO",
        "media_temperatura": (
            round(sum(temperaturas) / len(temperaturas), 1) if temperaturas else 0
        ),
        "total_alertas": len(alertas),
    }


def _get_bird_counts(now, lock, object_count, live_birds, BIRD_LIVE_TTL_SEC, BirdIdentity):
    global _cached_total_vistas, _cached_total_vistas_time
    if _cached_total_vistas is None or (now - _cached_total_vistas_time) > 60:
        _cached_total_vistas = BirdIdentity.query.count()
        _cached_total_vistas_time = now

    count = 0
    alive_count = 0
    if lock:
        with lock:
            count = object_count.get() if callable(object_count) else object_count
            alive_count = sum(
                1
                for info in live_birds.values()
                if (now - float(info["last_seen"])) <= BIRD_LIVE_TTL_SEC
            )
    else:
        count = object_count.get() if callable(object_count) else object_count
        alive_count = sum(
            1
            for info in live_birds.values()
            if (now - float(info["last_seen"])) <= BIRD_LIVE_TTL_SEC
        )
    return {
        "contagem_aves": count,
        "aves_vivas_individuais": alive_count,
        "total_aves_vistas": _cached_total_vistas,
    }


def _get_energy_summary(EnergyUsageDaily, ACTIVE_CAMERA_ID, today):
    energy_today = EnergyUsageDaily.query.filter_by(camera_id=ACTIVE_CAMERA_ID, day=today).first()
    vent_sec_today = float(energy_today.ventilacao_seconds) if energy_today else 0.0
    aq_sec_today = float(energy_today.aquecedor_seconds) if energy_today else 0.0
    return {
        "ventilacao_seconds": round(vent_sec_today, 2),
        "aquecedor_seconds": round(aq_sec_today, 2),
    }


def create_system_blueprint(deps):
    bp = Blueprint("system_api", __name__)

    # Extract all the required deps
    _utcnow = deps.get("utcnow")
    _require_permission = deps.get("require_permission")
    _guard_critical_action = deps.get("guard_critical_action")
    _audit = deps.get("audit")
    APP_START_TIME = deps.get("APP_START_TIME", time.time())
    t = deps.get("camera_thread")
    weekly_thread = deps.get("weekly_thread")
    mlops_thread = deps.get("mlops_thread")
    sync_thread = deps.get("sync_thread")
    weather_thread = deps.get("weather_thread")
    data_lifecycle_thread = deps.get("data_lifecycle_thread")
    MODO_DETECCAO = deps.get("MODO_DETECCAO")
    detector = deps.get("detector")
    TRACKER_CONFIG = deps.get("TRACKER_CONFIG")
    YOLO_MODEL_PATH = deps.get("YOLO_MODEL_PATH")
    _resolved_model_path = deps.get("resolved_model_path")
    BIRD_CLASS_NAME = deps.get("BIRD_CLASS_NAME")
    REID_MAX_GAP_SEC = deps.get("REID_MAX_GAP_SEC")
    REID_MAX_DISTANCE_RATIO = deps.get("REID_MAX_DISTANCE_RATIO")
    REID_APPEARANCE_MIN_SIM = deps.get("REID_APPEARANCE_MIN_SIM")
    CAMERA_INDEX = deps.get("CAMERA_INDEX")
    ACTIVE_CAMERA_ID = deps.get("active_camera_id")
    audio_classifier = deps.get("audio_classifier")
    COUGH_MODEL_PATH = deps.get("COUGH_MODEL_PATH")
    PLUGIN_MANAGER = deps.get("PLUGIN_MANAGER")
    PLUGINS_ROOT = deps.get("PLUGINS_ROOT")
    LOGGER = deps.get("LOGGER")
    SETTINGS = deps.get("settings")
    lock = deps.get("lock")
    object_count = deps.get("object_count")
    live_birds = deps.get("live_birds", {})
    BIRD_LIVE_TTL_SEC = deps.get("BIRD_LIVE_TTL_SEC", 5.0)
    _temperature_targets = deps.get("temperature_targets")
    _active_batch = deps.get("active_batch")
    estado_dispositivos = deps.get("estado_dispositivos")
    behavior_state = deps.get("behavior_state", {})
    sensor_state = deps.get("sensor_state", {})
    weight_state = deps.get("weight_state", {})
    acoustic_state = deps.get("acoustic_state", {})
    _energy_forecast = deps.get("energy_forecast")
    weather_state = deps.get("weather_state", {})
    tamper_state = deps.get("tamper_state", {})
    carcass_state = deps.get("carcass_state", {})
    _comfort_score = deps.get("comfort_score")

    @bp.route("/api/system-info", methods=["GET"])
    @require_auth()
    def get_system_info():
        uptime_seconds = int(time.time() - APP_START_TIME)
        return jsonify(
            {
                "uptime_seconds": uptime_seconds,
                "camera_thread_alive": t.is_alive() if t else False,
                "weekly_scheduler_alive": (weekly_thread.is_alive() if weekly_thread else False),
                "mlops_scheduler_alive": (mlops_thread.is_alive() if mlops_thread else False),
                "sync_thread_alive": sync_thread.is_alive() if sync_thread else False,
                "weather_thread_alive": (weather_thread.is_alive() if weather_thread else False),
                "data_lifecycle_thread_alive": (
                    data_lifecycle_thread.is_alive() if data_lifecycle_thread else False
                ),
                "modo_deteccao": MODO_DETECCAO,
                "yolo_loaded": detector.yolo_loaded if detector else False,
                "yolo_segmentation": (bool(detector.supports_segmentation) if detector else False),
                "tracker": TRACKER_CONFIG,
                "modelo_ia": YOLO_MODEL_PATH,
                "modelo_ia_resolvido": _resolved_model_path,
                "classe_ave": BIRD_CLASS_NAME,
                "reid_max_gap_sec": REID_MAX_GAP_SEC,
                "reid_max_distance_ratio": REID_MAX_DISTANCE_RATIO,
                "reid_appearance_min_sim": REID_APPEARANCE_MIN_SIM,
                "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "camera_index": CAMERA_INDEX,
                "active_camera_id": ACTIVE_CAMERA_ID,
                "cough_model_loaded": (
                    bool(audio_classifier.loaded) if audio_classifier else False
                ),
                "cough_model_path": COUGH_MODEL_PATH,
            }
        )

    @bp.route("/api/plugins", methods=["GET"])
    @require_auth()
    def get_plugins():
        items = PLUGIN_MANAGER.list_plugins() if PLUGIN_MANAGER else []
        return jsonify({"count": len(items), "plugins": items, "plugins_root": PLUGINS_ROOT})

    @bp.route("/api/plugins/reload", methods=["POST"])
    def reload_plugins():
        if _guard_critical_action:
            ok, resp = _guard_critical_action("plugins_reload")
            if not ok:
                return resp
        if PLUGIN_MANAGER:
            PLUGIN_MANAGER.load_all({"logger": LOGGER, "settings": SETTINGS})
            items = PLUGIN_MANAGER.list_plugins()
        else:
            items = []
        if _audit:
            _audit("plugins_reloaded", source="backend", details={"count": len(items)})
        return jsonify({"msg": "Plugins recarregados", "count": len(items), "plugins": items})

    @bp.route("/api/audit/logs", methods=["GET"])
    def audit_logs():
        if _require_permission:
            ok, resp = _require_permission("audit.read")
            if not ok:
                return resp
        limit = request.args.get("limit", default=200, type=int)
        limit = max(1, min(limit, 5000))
        rows = AuditLog.query.order_by(AuditLog.id.desc()).limit(limit).all()
        return jsonify({"count": len(rows), "items": [r.to_dict() for r in rows]})

    @bp.route("/api/status", methods=["GET"])
    @require_auth()
    def get_status():
        ultima = Reading.query.order_by(Reading.id.desc()).first()
        return jsonify(
            {
                "temperatura": ultima.temperatura if ultima else 0,
                "status": ultima.status if ultima else "INICIANDO",
                "active_camera": ACTIVE_CAMERA_ID,
            }
        )

    @bp.route("/api/history", methods=["GET"])
    @require_auth()
    def get_history():
        limit = request.args.get("limit", default=20, type=int)
        recentes = Reading.query.order_by(Reading.id.desc()).limit(limit).all()
        itens = []
        for r in reversed(recentes):
            itens.append(
                {
                    "hora": r.timestamp.strftime("%H:%M:%S"),
                    "temp": r.temperatura,
                    "status": r.status,
                }
            )
        return jsonify(itens)

    @bp.route("/api/chick_count", methods=["GET"])
    @require_auth()
    def get_chick_count():
        count = 0
        if lock:
            with lock:
                count = object_count.get() if callable(object_count) else object_count
        else:
            count = object_count.get() if callable(object_count) else object_count
        return jsonify({"count": count})

    def _build_behavior_data(behavior_state):
        return {
            "status": behavior_state.get("status", ""),
            "message": behavior_state.get("message", ""),
            "dispersion_ratio": behavior_state.get("dispersion_ratio", 0.0),
            "edge_ratio": behavior_state.get("edge_ratio", 0.0),
        }

    def _build_sensors_data(sensor_state):
        return {
            "humidity_pct": sensor_state.get("humidity_pct", 0),
            "ammonia_ppm": sensor_state.get("ammonia_ppm", 0),
            "feed_level_pct": sensor_state.get("feed_level_pct", 0),
            "water_level_pct": sensor_state.get("water_level_pct", 0),
        }

    def _build_automation_data(estado_dispositivos, targets):
        return {
            "enabled": (
                bool(estado_dispositivos.get("modo_automatico", False))
                if estado_dispositivos
                else False
            ),
            "targets": targets,
        }

    def _build_weight_data(weight_state, detector):
        return {
            "avg_weight_g": weight_state.get("avg_weight_g", 0),
            "ideal_weight_g": weight_state.get("ideal_weight_g", 0),
            "confidence": weight_state.get("confidence", 0),
            "method": (
                "segmentation_area"
                if (detector and getattr(detector, "supports_segmentation", False))
                else "bbox_area_fallback"
            ),
        }

    def _build_acoustic_data(acoustic_state, audio_classifier):
        return {
            "respiratory_health_index": acoustic_state.get("respiratory_health_index", 0),
            "cough_index": acoustic_state.get("cough_index", 0),
            "stress_audio_index": acoustic_state.get("stress_audio_index", 0),
            "source": acoustic_state.get("source", ""),
            "trained_model_loaded": (bool(audio_classifier.loaded) if audio_classifier else False),
        }

    def _build_tamper_data(tamper_state):
        return {
            "last_alert_ts": float(tamper_state.get("last_alert_ts", 0.0)),
            "last_causes": tamper_state.get("last_causes", []),
            "alerts_count": int(tamper_state.get("alerts_count", 0)),
        }

    def _build_carcass_data(carcass_state):
        return {
            "count": len(carcass_state.get("items", [])),
            "audio_alert": len(carcass_state.get("items", [])) > 0,
        }

    def _get_bird_counts(now, lock, object_count, live_birds, BIRD_LIVE_TTL_SEC, BirdIdentity):
        global _cached_total_vistas, _cached_total_vistas_time
        if _cached_total_vistas is None or (now - _cached_total_vistas_time) > 60:
            _cached_total_vistas = BirdIdentity.query.count()
            _cached_total_vistas_time = now

        count = 0
        alive_count = 0
        if lock:
            with lock:
                count = object_count.get() if callable(object_count) else object_count
                alive_count = sum(
                    1
                    for info in live_birds.values()
                    if (now - float(info["last_seen"])) <= BIRD_LIVE_TTL_SEC
                )
        else:
            count = object_count.get() if callable(object_count) else object_count
            alive_count = sum(
                1
                for info in live_birds.values()
                if (now - float(info["last_seen"])) <= BIRD_LIVE_TTL_SEC
            )
        return {
            "contagem_aves": count,
            "aves_vivas_individuais": alive_count,
            "total_aves_vistas": _cached_total_vistas,
        }

    def _get_energy_summary(EnergyUsageDaily, ACTIVE_CAMERA_ID, today):
        energy_today = EnergyUsageDaily.query.filter_by(
            camera_id=ACTIVE_CAMERA_ID, day=today
        ).first()
        vent_sec_today = float(energy_today.ventilacao_seconds) if energy_today else 0.0
        aq_sec_today = float(energy_today.aquecedor_seconds) if energy_today else 0.0
        return {
            "ventilacao_seconds": round(vent_sec_today, 2),
            "aquecedor_seconds": round(aq_sec_today, 2),
        }

    @bp.route("/api/summary", methods=["GET"])
    @require_auth()
    def get_summary():
        temp_summary = _get_temperature_summary(Reading)
        now = time.time()
        bird_counts = _get_bird_counts(
            now, lock, object_count, live_birds, BIRD_LIVE_TTL_SEC, BirdIdentity
        )

        targets = _temperature_targets(ACTIVE_CAMERA_ID) if _temperature_targets else {}
        batch = _active_batch(ACTIVE_CAMERA_ID) if _active_batch else None
        pending_sync = SyncQueueItem.query.filter_by(status="pending").count()
        today = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        energy_summary = _get_energy_summary(EnergyUsageDaily, ACTIVE_CAMERA_ID, today)

        return jsonify(
            {
                **temp_summary,
                **bird_counts,
                "metodo_temperatura_ave": "estimada_rgb_proxy",
                "tracker": TRACKER_CONFIG,
                "classe_ave": BIRD_CLASS_NAME,
                "dispositivos": estado_dispositivos,
                "modo_deteccao": MODO_DETECCAO,
                "camera_id": ACTIVE_CAMERA_ID,
                "behavior": _build_behavior_data(behavior_state),
                "sensors": _build_sensors_data(sensor_state),
                "automation": _build_automation_data(estado_dispositivos, targets),
                "batch": batch.to_dict() if batch else None,
                "weight": _build_weight_data(weight_state, detector),
                "acoustic": _build_acoustic_data(acoustic_state, audio_classifier),
                "energy_today": energy_summary,
                "smart_grid_forecast_12h": (_energy_forecast(hours=12) if _energy_forecast else []),
                "sync": {"pending": pending_sync},
                "weather": weather_state,
                "tamper": _build_tamper_data(tamper_state),
                "carcass": _build_carcass_data(carcass_state),
                "comfort_score": _comfort_score() if _comfort_score else 0,
            }
        )

    @bp.route("/api/events", methods=["GET"])
    @require_auth()
    def get_events():
        limit = request.args.get("limit", default=100, type=int)
        limit = max(1, min(limit, 2000))
        rows = (
            EventLog.query.filter_by(camera_id=ACTIVE_CAMERA_ID)
            .order_by(EventLog.id.desc())
            .limit(limit)
            .all()
        )
        return jsonify({"count": len(rows), "items": [row.to_dict() for row in rows]})

    @bp.route("/api/alerts", methods=["GET"])
    @require_auth()
    def get_alerts():
        itens = []

        recentes = (
            Reading.query.filter(Reading.status != "NORMAL")
            .order_by(Reading.id.desc())
            .limit(50)
            .all()
        )
        for item in recentes:
            nivel = "alto" if item.status == "CALOR" else "medio"
            itens.append(
                {
                    "id": f"temp-{item.id}",
                    "tipo": item.status,
                    "nivel": nivel,
                    "mensagem": f"Temperatura em estado {item.status}",
                    "temperatura": item.temperatura,
                    "hora": item.timestamp.strftime("%H:%M:%S"),
                    "data": item.timestamp.strftime("%d/%m/%Y"),
                    "_ts": item.timestamp,
                }
            )

        event_rows = (
            EventLog.query.filter_by(camera_id=ACTIVE_CAMERA_ID)
            .order_by(EventLog.id.desc())
            .limit(50)
            .all()
        )
        for ev in event_rows:
            itens.append(
                {
                    "id": f"event-{ev.id}",
                    "tipo": ev.event_type.upper(),
                    "nivel": (
                        "alto"
                        if ev.level == "high"
                        else "medio"
                        if ev.level == "medium"
                        else "baixo"
                    ),
                    "mensagem": ev.message,
                    "temperatura": None,
                    "hora": ev.timestamp.strftime("%H:%M:%S"),
                    "data": ev.timestamp.strftime("%d/%m/%Y"),
                    "_ts": ev.timestamp,
                }
            )

        itens.sort(key=lambda x: x["_ts"], reverse=True)
        for item in itens:
            item.pop("_ts", None)

        return jsonify(itens[:100])

    @bp.route("/api/weather/forecast", methods=["GET"])
    @require_auth()
    def weather_forecast():
        return jsonify(weather_state)

    add_remaining_routes(bp, deps)
    return bp
