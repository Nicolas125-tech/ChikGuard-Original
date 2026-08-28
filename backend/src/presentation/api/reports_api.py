import os

from flask import Blueprint, current_app, jsonify, request, send_file

from database import Batch, WeightEstimate
from src.ai.forecast import predict_slaughter_date
from src.reports.generator import _send_report_email, generate_esg_report, generate_weekly_report
from src.security.auth import require_auth
from src.security.rate_limiter import limiter


def _generate_esg(active_camera_id, utcnow_func, log_event):
    data = request.get_json(silent=True) or {}
    days = int(data.get("days", 30))
    email = str(data.get("email", "")).strip() or None
    if email and len(email) > 100:
        return jsonify({"msg": "Tamanho de email excede o limite"}), 400
    try:
        path = generate_esg_report(
            current_app.app_context, active_camera_id, utcnow_func, days=days
        )
    except Exception as exc:
        import logging

        logging.getLogger(__name__).error("Falha ao gerar PDF ESG: %s", str(exc))
        return jsonify({"msg": "Falha interna ao gerar PDF ESG"}), 500

    email_status = None
    if email:
        ok, detail = _send_report_email(path, email)
        email_status = {"sent": ok, "detail": detail, "email": email}

    log_event(
        event_type="esg_report",
        level="info",
        message="Relatorio ESG gerado",
        metadata={"file": path, "days": days, "email_status": email_status},
    )
    return jsonify({"msg": "Relatorio ESG gerado", "file": path, "email_status": email_status})


def _download_esg(active_camera_id, utcnow_func):
    days = request.args.get("days", default=30, type=int)
    try:
        path = generate_esg_report(
            current_app.app_context, active_camera_id, utcnow_func, days=days
        )
        return send_file(
            path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=os.path.basename(path),
        )
    except Exception as exc:
        import logging

        logging.getLogger(__name__).error("Falha ao gerar/exportar PDF ESG: %s", str(exc))
        return jsonify({"msg": "Falha interna ao gerar/exportar PDF ESG"}), 500


def _get_batch_passport(utcnow_func):
    active_batch = Batch.query.filter_by(active=True).first()
    if not active_batch:
        return jsonify(
            {
                "passport_id": "ND-0000",
                "batch_name": "Nenhum Lote Ativo",
                "status": "Inativo",
                "start_date": "N/A",
                "current_age_days": 0,
                "initial_count": 0,
                "mortality_rate": 0,
                "avg_temperature": 0,
                "stress_events": 0,
                "medications": [],
                "certification": "Pendente",
            }
        )

    # Calcula idade
    start = active_batch.start_date
    now = utcnow_func()
    age_days = (now - start).days if start else 0

    # Simula agregacao rapida pro passaporte
    mort_rate = (
        round((active_batch.current_mortality / active_batch.initial_count) * 100, 2)
        if active_batch.initial_count > 0
        else 0
    )

    passport_data = {
        "passport_id": f"CG-PT-{active_batch.id}-{now.strftime('%Y%m')}",
        "batch_name": active_batch.name,
        "status": "Em andamento" if active_batch.active else "Finalizado",
        "start_date": start.strftime("%d/%m/%Y") if start else "N/A",
        "current_age_days": age_days,
        "initial_count": active_batch.initial_count,
        "mortality_rate": mort_rate,
        "avg_temperature": 27.5,  # Simulado, poderia agregar SensorReadings
        "stress_events": 2,  # Simulado
        "medications": ["Vacina Newcastle (Dia 7)", "Anticoccidiano (Preventivo)"],
        "certification": "Aprovado - Padrão Ouro Exportação" if mort_rate < 3.0 else "Regular",
    }
    return jsonify(passport_data)


def _generate_weekly(active_camera_id, utcnow_func, log_event):
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip() or None
    if email and len(email) > 100:
        return jsonify({"msg": "Tamanho de email excede o limite"}), 400
    try:
        path = generate_weekly_report(current_app.app_context, active_camera_id, utcnow_func)
    except Exception as exc:
        import logging

        logging.getLogger(__name__).error("Falha ao gerar PDF: %s", str(exc))
        return jsonify({"msg": "Falha interna ao gerar PDF"}), 500

    email_status = None
    if email:
        ok, detail = _send_report_email(path, email)
        email_status = {"sent": ok, "detail": detail, "email": email}

    log_event(
        event_type="weekly_report",
        level="info",
        message="Relatorio semanal gerado manualmente",
        metadata={"file": path, "email_status": email_status},
    )
    return jsonify({"msg": "Relatorio gerado", "file": path, "email_status": email_status})


def _download_weekly(active_camera_id, utcnow_func, log_event):
    try:
        path = generate_weekly_report(current_app.app_context, active_camera_id, utcnow_func)
        log_event(
            event_type="weekly_report",
            level="info",
            message="Relatorio semanal exportado pelo painel",
            metadata={"file": path},
        )
        return send_file(
            path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=os.path.basename(path),
        )
    except Exception as exc:
        import logging

        logging.getLogger(__name__).error("Falha ao gerar/exportar PDF: %s", str(exc))
        return jsonify({"msg": "Falha interna ao gerar/exportar PDF"}), 500


def _get_weight_forecast(active_camera_id):
    target_weight = request.args.get("target_weight", default=2800.0, type=float)

    batch = Batch.query.filter_by(camera_id=active_camera_id, active=True).first()
    if not batch:
        return jsonify({"error": "Nenhum lote ativo encontrado"}), 404

    start_date = batch.start_date

    weights = (
        WeightEstimate.query.filter(
            WeightEstimate.camera_id == active_camera_id, WeightEstimate.timestamp >= start_date
        )
        .order_by(WeightEstimate.timestamp.asc())
        .all()
    )

    if not weights:
        return jsonify({"error": "Sem dados de peso para prever"}), 400

    daily_weights = {}
    for w in weights:
        day_diff = (w.timestamp - start_date).days
        if day_diff not in daily_weights:
            daily_weights[day_diff] = []
        daily_weights[day_diff].append(w.avg_weight_g)

    weight_data = []
    for day, vals in daily_weights.items():
        weight_data.append({"day": day, "avg_weight": sum(vals) / len(vals)})

    forecast = predict_slaughter_date(weight_data, start_date, target_weight=target_weight)

    if not forecast:
        return jsonify(
            {"error": "Dados insuficientes (mínimo de 3 dias de medição necessários)"}
        ), 400

    return jsonify(
        {
            "batch_id": batch.id,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "current_day": max(daily_weights.keys()),
            "forecast": forecast,
        }
    )


def _get_mortality_forecast(active_camera_id):
    from datetime import datetime, timedelta

    from database import Batch, SensorReading

    batch = Batch.query.filter_by(camera_id=active_camera_id, active=True).first()
    if not batch:
        return jsonify({"error": "Nenhum lote ativo encontrado"}), 404

    start_date = batch.start_date
    current_day = (datetime.utcnow() - start_date).days
    if current_day < 0:
        current_day = 0

    # Calculate recent thermal stress
    readings = (
        SensorReading.query.filter(SensorReading.camera_id == active_camera_id)
        .order_by(SensorReading.timestamp.desc())
        .limit(100)
        .all()
    )

    avg_temp = 25.0
    if readings:
        valid_temps = [r.temperature_c for r in readings if r.temperature_c is not None]
        if valid_temps:
            avg_temp = sum(valid_temps) / len(valid_temps)

    # Simple ML-like mortality projection based on Age and Thermal stress
    projections = []

    # Calculate past 3 and future 7 days
    for i in range(-3, 8):
        day = current_day + i
        if day < 1:
            continue

        # Base daily mortality rate in %
        base_rate = 0.05
        if day < 7:
            base_rate = 0.12  # chick phase
        elif day > 35:
            base_rate = 0.08  # heavy bird phase

        # Stress multiplier
        stress_mult = 1.0
        if avg_temp > 29.0:
            stress_mult = 1.0 + (avg_temp - 29.0) * 0.5
        elif avg_temp < 21.0:
            stress_mult = 1.0 + (21.0 - avg_temp) * 0.3

        daily_risk = base_rate * stress_mult

        if i <= 0:
            # Mock actual past
            daily_risk = daily_risk * 0.9

        projections.append(
            {
                "day": day,
                "date": (datetime.utcnow() + timedelta(days=i)).strftime("%Y-%m-%d"),
                "risk_pct": round(daily_risk, 3),
                "is_forecast": i > 0,
                "stress_factor": round(stress_mult, 2),
            }
        )

    return jsonify(
        {
            "batch_id": batch.id,
            "current_day": current_day,
            "avg_recent_temp": round(avg_temp, 1),
            "projections": projections,
        }
    )


def create_reports_blueprint(deps):
    bp = Blueprint("reports_api", __name__)

    active_camera_id = deps.get("active_camera_id")
    log_event = deps.get("log_event")
    utcnow_func = deps.get("utcnow")

    @bp.route("/api/reports/esg", methods=["POST"])
    @require_auth()
    def generate_esg():
        return _generate_esg(active_camera_id, utcnow_func, log_event)

    @bp.route("/api/reports/esg/download", methods=["GET"])
    @require_auth()
    @limiter.limit("5 per minute")
    def download_esg():
        return _download_esg(active_camera_id, utcnow_func)

    @bp.route("/api/reports/passport", methods=["GET"])
    @require_auth()
    def get_batch_passport():
        return _get_batch_passport(utcnow_func)

    @bp.route("/api/reports/weekly", methods=["POST"])
    @require_auth()
    @limiter.limit("5 per minute")
    def generate_weekly():
        return _generate_weekly(active_camera_id, utcnow_func, log_event)

    @bp.route("/api/reports/weekly/download", methods=["GET"])
    @require_auth()
    @limiter.limit("5 per minute")
    def download_weekly():
        return _download_weekly(active_camera_id, utcnow_func, log_event)

    @bp.route("/api/forecast/weight", methods=["GET"])
    @require_auth()
    def get_weight_forecast():
        return _get_weight_forecast(active_camera_id)

    @bp.route("/api/forecast/mortality", methods=["GET"])
    @require_auth()
    def get_mortality_forecast():
        return _get_mortality_forecast(active_camera_id)

    return bp
