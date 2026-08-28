from datetime import datetime

from flask import Blueprint, jsonify, request

from database import EnergyUsageDaily
from src.security.auth import require_auth


def create_energy_blueprint(deps):
    bp = Blueprint("energy_api", __name__)

    _utcnow = deps.get("utcnow")
    _energy_forecast = deps.get("energy_forecast")
    ACTIVE_CAMERA_ID = deps.get("active_camera_id")
    VENTILACAO_POWER_KW = deps.get("VENTILACAO_POWER_KW", 1.5)
    AQUECEDOR_POWER_KW = deps.get("AQUECEDOR_POWER_KW", 2.0)
    ENERGY_TARIFF_PER_KWH = deps.get("ENERGY_TARIFF_PER_KWH", 0.65)

    @bp.route("/api/energy/summary", methods=["GET"])
    @require_auth()
    def energy_summary():
        now = _utcnow()
        month_start = datetime(now.year, now.month, 1)
        rows = (
            EnergyUsageDaily.query.filter(
                EnergyUsageDaily.camera_id == ACTIVE_CAMERA_ID, EnergyUsageDaily.day >= month_start
            )
            .order_by(EnergyUsageDaily.day.asc())
            .all()
        )
        fan_sec = sum(float(r.ventilacao_seconds or 0.0) for r in rows)
        heater_sec = sum(float(r.aquecedor_seconds or 0.0) for r in rows)
        fan_kwh = (fan_sec / 3600.0) * VENTILACAO_POWER_KW
        heater_kwh = (heater_sec / 3600.0) * AQUECEDOR_POWER_KW
        total_kwh = fan_kwh + heater_kwh
        cost = total_kwh * ENERGY_TARIFF_PER_KWH
        savings = cost * 0.18
        return jsonify(
            {
                "camera_id": ACTIVE_CAMERA_ID,
                "month": month_start.strftime("%Y-%m"),
                "ventilacao_seconds": round(fan_sec, 2),
                "aquecedor_seconds": round(heater_sec, 2),
                "total_kwh": round(total_kwh, 3),
                "tariff_per_kwh": ENERGY_TARIFF_PER_KWH,
                "estimated_cost": round(cost, 2),
                "suggestion": f"Se reduzir a temperatura-alvo em 0.5C, a economia estimada e de R$ {savings:.2f}.",
            }
        )

    @bp.route("/api/energy/forecast", methods=["GET"])
    @require_auth()
    def energy_forecast():
        hours = request.args.get("hours", default=12, type=int)
        # Note: _energy_forecast uses app context, which should be active during request
        forecast = _energy_forecast(hours=hours) if _energy_forecast else []
        return jsonify(forecast)

    return bp
