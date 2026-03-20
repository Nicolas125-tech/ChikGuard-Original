from flask import Blueprint, jsonify, request

def create_devices_blueprint(deps):
    bp = Blueprint("devices_api", __name__)

    # dependencies
    guard_critical_action = deps.get("guard_critical_action")
    log_event = deps.get("log_event")
    audit = deps.get("audit")
    estado_dispositivos = deps.get("estado_dispositivos")
    auto_config = deps.get("auto_config")
    active_camera_id = deps.get("active_camera_id")
    temperature_targets = deps.get("temperature_targets")

    @bp.route("/api/auto-mode", methods=["GET", "POST"])
    def auto_mode():
        if request.method == "GET":
            targets = temperature_targets(active_camera_id)
            return jsonify(
                {
                    "enabled": bool(estado_dispositivos["modo_automatico"]),
                    "config": auto_config,
                    "effective_targets": targets,
                    "camera_id": active_camera_id,
                }
            )

        ok, resp = guard_critical_action("auto_mode_change", permission="automation.manage")
        if not ok:
            return resp

        data = request.get_json(silent=True) or {}
        if "enabled" in data:
            estado_dispositivos["modo_automatico"] = bool(data["enabled"])
        for key in ("fan_on_temp", "fan_off_temp", "heater_on_temp", "heater_off_temp"):
            if key in data:
                auto_config[key] = float(data[key])
        if "use_batch_curve" in data:
            auto_config["use_batch_curve"] = bool(data["use_batch_curve"])

        log_event(
            event_type="auto_mode_config",
            level="info",
            message=f"Modo automatico {'ativado' if estado_dispositivos['modo_automatico'] else 'desativado'}",
            metadata={"config": auto_config},
        )
        audit(
            "auto_mode_changed",
            source="manual",
            details={"enabled": estado_dispositivos["modo_automatico"], "config": auto_config},
        )
        return jsonify({"enabled": estado_dispositivos["modo_automatico"], "config": auto_config})


    @bp.route("/api/ventilacao", methods=["POST"])
    def controlar_ventilacao():
        data = request.get_json(silent=True) or {}
        if "ligar" not in data:
            return jsonify({"msg": "Parametro 'ligar' e obrigatorio"}), 400

        ligar = bool(data["ligar"])
        perm = "device.power_on" if ligar else "device.power_off"
        ok, resp = guard_critical_action("ventilacao_toggle", permission=perm)
        if not ok:
            return resp

        estado_dispositivos["ventilacao"] = ligar
        log_event(
            event_type="manual_device_action",
            level="info",
            message=f"Ventilacao {'ligada' if estado_dispositivos['ventilacao'] else 'desligada'} manualmente",
        )
        audit(
            "manual_ventilacao_toggle",
            source="manual",
            details={"ligar": estado_dispositivos["ventilacao"]},
        )
        return jsonify(
            {
                "ventilacao": estado_dispositivos["ventilacao"],
                "msg": "Ventilacao ligada" if estado_dispositivos["ventilacao"] else "Ventilacao desligada",
            }
        )

    @bp.route("/api/aquecedor", methods=["POST"])
    def controlar_aquecedor():
        data = request.get_json(silent=True) or {}
        if "ligar" not in data:
            return jsonify({"msg": "Parametro 'ligar' e obrigatorio"}), 400

        ligar = bool(data["ligar"])
        perm = "device.power_on" if ligar else "device.power_off"
        ok, resp = guard_critical_action("aquecedor_toggle", permission=perm)
        if not ok:
            return resp

        estado_dispositivos["aquecedor"] = ligar
        log_event(
            event_type="manual_device_action",
            level="info",
            message=f"Aquecedor {'ligado' if estado_dispositivos['aquecedor'] else 'desligado'} manualmente",
        )
        audit(
            "manual_aquecedor_toggle",
            source="manual",
            details={"ligar": estado_dispositivos["aquecedor"]},
        )
        return jsonify(
            {
                "aquecedor": estado_dispositivos["aquecedor"],
                "msg": "Aquecedor ligado" if estado_dispositivos["aquecedor"] else "Aquecedor desligado",
            }
        )

    @bp.route("/api/luz-dimmer", methods=["GET", "POST"])
    def controlar_luz_dimmer():
        if request.method == "GET":
            return jsonify({"luz_intensidade_pct": int(estado_dispositivos.get("luz_intensidade_pct", 0))})

        ok, resp = guard_critical_action("light_dimmer_change", permission="lighting.manage")
        if not ok:
            return resp

        data = request.get_json(silent=True) or {}
        intensidade = int(data.get("intensidade_pct", 0))
        intensidade = max(0, min(100, intensidade))
        estado_dispositivos["luz_intensidade_pct"] = intensidade

        log_event("light_dimmer_changed", "info", f"Intensidade da luz ajustada para {intensidade}%")
        audit("light_dimmer_changed", source="manual", details={"intensidade_pct": intensidade})
        return jsonify({"luz_intensidade_pct": intensidade, "msg": "Dimmer atualizado"})

    @bp.route("/api/estado-dispositivos", methods=["GET"])
    def get_estado_dispositivos():
        return jsonify(estado_dispositivos)

    return bp
