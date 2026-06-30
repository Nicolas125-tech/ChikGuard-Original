import time

from flask import Blueprint, jsonify, request

from src.security.auth import require_auth


def create_sensors_blueprint(deps):
    bp = Blueprint("sensors_api", __name__)

    active_camera_id = deps.get("active_camera_id")
    sensor_state = deps.get("sensor_state")
    sensor_thresholds = deps.get("sensor_thresholds")
    SensorReading = deps.get("SensorReading")
    ThermalAnomaly = deps.get("ThermalAnomaly")
    AcousticReading = deps.get("AcousticReading")
    acoustic_state = deps.get("acoustic_state")
    audio_classifier = deps.get("audio_classifier")
    persist_sensor_reading = deps.get("persist_sensor_reading")
    evaluate_sensor_alerts = deps.get("evaluate_sensor_alerts")
    log_event = deps.get("log_event")
    audit = deps.get("audit")
    db = deps.get("db")
    enqueue_sync_item = deps.get("enqueue_sync_item")
    utcnow = deps.get("utcnow")
    timedelta = deps.get("timedelta")
    sf = deps.get("sf")
    io = deps.get("io")
    np = deps.get("np")

    @bp.route("/api/sensors/live", methods=["GET"])
    @require_auth()
    def get_sensors_live():
        return jsonify(
            {
                "camera_id": active_camera_id,
                "temperature_c": sensor_state["temperature_c"],
                "humidity_pct": sensor_state["humidity_pct"],
                "ammonia_ppm": sensor_state["ammonia_ppm"],
                "feed_level_pct": sensor_state["feed_level_pct"],
                "water_level_pct": sensor_state["water_level_pct"],
                "source": sensor_state["source"],
                "updated_at_epoch": sensor_state["updated_at"],
                "thresholds": sensor_thresholds,
            }
        )

    @bp.route("/api/sensors/history", methods=["GET"])
    @require_auth()
    def get_sensors_history():
        limit = request.args.get("limit", default=100, type=int)
        limit = max(1, min(limit, 5000))
        rows = (
            SensorReading.query.filter_by(tenant_id=request.tenant_id, camera_id=active_camera_id)
            .order_by(SensorReading.id.desc())
            .limit(limit)
            .all()
        )
        return jsonify({"count": len(rows), "items": [r.to_dict() for r in reversed(rows)]})

    @bp.route("/api/sensors/ingest", methods=["POST"])
    @require_auth()
    def ingest_sensor_data():
        payload = request.get_json(silent=True) or {}
        required = [
            "temperature_c",
            "humidity_pct",
            "ammonia_ppm",
            "feed_level_pct",
            "water_level_pct",
        ]
        missing = [k for k in required if k not in payload]
        if missing:
            return jsonify({"msg": f"Campos obrigatorios ausentes: {', '.join(missing)}"}), 400

        sensor_state.update(
            {
                "temperature_c": float(payload["temperature_c"]),
                "humidity_pct": float(payload["humidity_pct"]),
                "ammonia_ppm": float(payload["ammonia_ppm"]),
                "feed_level_pct": float(payload["feed_level_pct"]),
                "water_level_pct": float(payload["water_level_pct"]),
                "source": str(payload.get("source", "external")),
                "updated_at": time.time(),
            }
        )
        persist_sensor_reading(source=sensor_state["source"])
        evaluate_sensor_alerts()
        return jsonify({"msg": "Leitura de sensores recebida", "state": sensor_state}), 200

    @bp.route("/api/thermal-anomalies/live", methods=["GET"])
    @require_auth()
    def thermal_anomalies_live():
        last_minutes = request.args.get("minutes", default=20, type=int)
        start = utcnow() - timedelta(minutes=max(1, min(last_minutes, 240)))
        rows = (
            ThermalAnomaly.query.filter(
                ThermalAnomaly.camera_id == active_camera_id, ThermalAnomaly.timestamp >= start
            )
            .order_by(ThermalAnomaly.id.desc())
            .limit(200)
            .all()
        )
        items = [r.to_dict() for r in rows]
        sectors = sorted(list({i["sector"] for i in items if i.get("sector")}))
        return jsonify({"count": len(items), "sectors": sectors, "items": items})

    @bp.route("/api/acoustic/live", methods=["GET"])
    @require_auth()
    def acoustic_live():
        return jsonify(
            {
                "camera_id": active_camera_id,
                "respiratory_health_index": acoustic_state["respiratory_health_index"],
                "cough_index": acoustic_state["cough_index"],
                "stress_audio_index": acoustic_state["stress_audio_index"],
                "source": acoustic_state["source"],
                "updated_at_epoch": acoustic_state["updated_at"],
            }
        )

    @bp.route("/api/acoustic/history", methods=["GET"])
    @require_auth()
    def acoustic_history():
        limit = request.args.get("limit", default=200, type=int)
        limit = max(1, min(limit, 5000))
        rows = (
            AcousticReading.query.filter_by(tenant_id=request.tenant_id, camera_id=active_camera_id)
            .order_by(AcousticReading.id.desc())
            .limit(limit)
            .all()
        )
        return jsonify({"count": len(rows), "items": [r.to_dict() for r in reversed(rows)]})

    @bp.route("/api/acoustic/classify", methods=["POST"])
    @require_auth()
    def acoustic_classify():
        if not audio_classifier.loaded:
            return jsonify(
                {"msg": "Modelo de tosse nao carregado", "model_error": audio_classifier.last_error}
            ), 400
        if sf is None:
            return jsonify({"msg": "Dependencia soundfile nao disponivel no backend"}), 500

        f = request.files.get("audio")
        if f is None:
            return jsonify({"msg": "Envie arquivo de audio no campo 'audio'"}), 400

        try:
            # Limite de 5MB para evitar DoS por arquivos gigantes
            raw = f.read(5 * 1024 * 1024 + 1)
            if len(raw) > 5 * 1024 * 1024:
                return jsonify({"msg": "Arquivo de audio muito grande (max 5MB)"}), 413
            y, sr = sf.read(io.BytesIO(raw), always_2d=False)
            if isinstance(y, np.ndarray) and y.ndim > 1:
                y = np.mean(y, axis=1)

            result = audio_classifier.classify(y, int(sr))
            if result is None:
                return jsonify(
                    {"msg": "Falha na inferencia de tosse", "error": audio_classifier.last_error}
                ), 500

            acoustic_state.update(
                {
                    "respiratory_health_index": float(result["respiratory_health_index"]),
                    "cough_index": float(result["cough_index"]),
                    "stress_audio_index": float(result["stress_audio_index"]),
                    "source": "trained_model",
                    "updated_at": time.time(),
                }
            )

            row = AcousticReading(
                tenant_id=request.tenant_id,
                camera_id=active_camera_id,
                respiratory_health_index=acoustic_state["respiratory_health_index"],
                cough_index=acoustic_state["cough_index"],
                stress_audio_index=acoustic_state["stress_audio_index"],
                source="trained_model",
            )

            # db interaction without app_context explicitly if this is run inside a request
            db.session.add(row)
            db.session.commit()
            enqueue_sync_item("acoustic_reading", row.to_dict())

            if acoustic_state["cough_index"] > 60:
                log_event(
                    event_type="respiratory_alert",
                    level="high",
                    message="Pico de tosse detectado por modelo acustico treinado",
                    metadata={
                        "cough_index": acoustic_state["cough_index"],
                        "source": "trained_model",
                    },
                )
            audit(
                "acoustic_file_classified",
                source="manual",
                details={"source": "trained_model", "cough_index": acoustic_state["cough_index"]},
            )
            return jsonify({"msg": "Audio classificado com sucesso", "result": acoustic_state})

        except Exception as exc:
            import logging

            logging.getLogger(__name__).error("Falha ao processar audio: %s", str(exc))
            return jsonify({"msg": "Falha interna ao processar audio"}), 500

    @bp.route("/api/sensors/anomaly", methods=["GET"])
    @require_auth()
    def check_anomaly():
        # Busca o historico das ultimas 24h para baseline (treino da floresta)
        start = utcnow() - timedelta(hours=24)
        sensors = (
            SensorReading.query.filter(
                SensorReading.camera_id == active_camera_id, SensorReading.timestamp >= start
            )
            .order_by(SensorReading.timestamp.desc())
            .limit(100)
            .all()
        )

        from src.ai.anomaly import detect_multivariate_anomaly

        history = []
        for s in sensors:
            history.append(
                {
                    "temp": s.temperature_c or 0,
                    "hum": s.humidity_pct or 0,
                    "amm": s.ammonia_ppm or 0,
                    "cough": 0,  # Em producao mesclariamos os timestamps
                }
            )

        current = {
            "temp": sensor_state.get("temperature_c", 0),
            "hum": sensor_state.get("humidity_pct", 0),
            "amm": sensor_state.get("ammonia_ppm", 0),
            "cough": acoustic_state.get("cough_index", 0),
        }

        # Fallback de seguranca para evitar crashes em setups novos (bootstrap do dataset)
        if len(history) < 20:
            history = [current] * 25

        result = detect_multivariate_anomaly(history, current)

        # Dispara alerta global no sistema se detectar uma doenca multivariada invisivel
        if result.get("is_anomaly"):
            log_event(
                event_type="multivariate_anomaly",
                level="high",
                message="IA Detectou padrao anomalo multivariado (Isolation Forest)!",
                metadata=result,
            )

        return jsonify(result)

    @bp.route("/api/ai/spatial/huddling", methods=["GET"])
    @require_auth()
    def check_huddling():
        # Pegar historico de tracking x,y das aves nos ultimos 3 minutos
        from database import BirdTrackPoint

        start = utcnow() - timedelta(minutes=3)

        points = BirdTrackPoint.query.filter(
            BirdTrackPoint.tenant_id == request.tenant_id, BirdTrackPoint.timestamp >= start
        ).all()

        pts_list = [{"x": p.x, "y": p.y} for p in points]

        from src.ai.spatial import detect_huddling

        result = detect_huddling(pts_list)

        if result.get("huddling_detected"):
            log_event(
                event_type="spatial_anomaly",
                level="high",
                message="IA Espacial (DBSCAN) detectou aves amontoadas! Possivel corrente de ar frio.",
                metadata=result,
            )

        return jsonify(result)

    return bp
