import os
from flask import Blueprint, jsonify, request, send_file, current_app
from src.reports.generator import generate_esg_report, generate_weekly_report, _send_report_email
from src.security.auth import require_auth
from src.security.rate_limiter import limiter
from database import db, Batch, WeightEstimate
from src.ai.forecast import predict_slaughter_date

def create_reports_blueprint(deps):
    bp = Blueprint("reports_api", __name__)

    active_camera_id = deps.get("active_camera_id")
    log_event = deps.get("log_event")
    utcnow_func = deps.get("utcnow")

    @bp.route("/api/reports/esg", methods=["POST"])
    @require_auth()
    def generate_esg():
        data = request.get_json(silent=True) or {}
        days = int(data.get("days", 30))
        email = str(data.get("email", "")).strip() or None
        try:
            path = generate_esg_report(
                current_app.app_context, active_camera_id, utcnow_func, days=days
            )
        except Exception as exc:
            import logging

            logging.getLogger(__name__).error("Falha ao gerar PDF ESG: %s", exc)
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

    @bp.route("/api/reports/esg/download", methods=["GET"])
    @require_auth()
    @limiter.limit("5 per minute")
    def download_esg():
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

            logging.getLogger(__name__).error("Falha ao gerar/exportar PDF ESG: %s", exc)
            return jsonify({"msg": "Falha interna ao gerar/exportar PDF ESG"}), 500

    @bp.route("/api/reports/weekly", methods=["POST"])
    @require_auth()
    @limiter.limit("5 per minute")
    def generate_weekly():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip() or None
        try:
            path = generate_weekly_report(current_app.app_context, active_camera_id, utcnow_func)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).error("Falha ao gerar PDF: %s", exc)
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

    @bp.route("/api/reports/weekly/download", methods=["GET"])
    @require_auth()
    @limiter.limit("5 per minute")
    def download_weekly():
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

            logging.getLogger(__name__).error("Falha ao gerar/exportar PDF: %s", exc)
            return jsonify({"msg": "Falha interna ao gerar/exportar PDF"}), 500

    @bp.route("/api/forecast/weight", methods=["GET"])
    @require_auth()
    def get_weight_forecast():
        target_weight = request.args.get("target_weight", default=2800.0, type=float)
        
        batch = Batch.query.filter_by(camera_id=active_camera_id, active=True).first()
        if not batch:
            return jsonify({"error": "Nenhum lote ativo encontrado"}), 404
            
        start_date = batch.start_date
        
        weights = WeightEstimate.query.filter(
            WeightEstimate.camera_id == active_camera_id,
            WeightEstimate.timestamp >= start_date
        ).order_by(WeightEstimate.timestamp.asc()).all()
        
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
            weight_data.append({"day": day, "avg_weight": sum(vals)/len(vals)})
            
        forecast = predict_slaughter_date(weight_data, start_date, target_weight=target_weight)
        
        if not forecast:
            return jsonify({"error": "Dados insuficientes (mínimo de 3 dias de medição necessários)"}), 400
            
        return jsonify({
            "batch_id": batch.id,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "current_day": max(daily_weights.keys()),
            "forecast": forecast
        })

    return bp
