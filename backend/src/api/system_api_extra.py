from flask import jsonify, request

from src.security.auth import require_auth


def _add_acoustic_routes(bp, deps):
    audio_classifier = deps.get("audio_classifier")
    acoustic_state = deps.get("acoustic_state", {})

    @bp.route("/api/acoustic/model-info", methods=["GET"])
    @require_auth()
    def acoustic_model_info():
        return jsonify(
            {
                "loaded": bool(audio_classifier.loaded) if audio_classifier else False,
                "classes": audio_classifier.classes
                if audio_classifier and hasattr(audio_classifier, "classes")
                else [],
                "device": str(audio_classifier.device)
                if audio_classifier and hasattr(audio_classifier, "device")
                else "cpu",
                "total_inferences": acoustic_state.get("total_inferences", 0),
                "last_inference_ms": acoustic_state.get("last_inference_ms", 0),
            }
        )


def _add_voice_routes(bp, deps):
    _guard_critical_action = deps.get("guard_critical_action")
    estado_dispositivos = deps.get("estado_dispositivos", {})
    _audit = deps.get("audit")

    @bp.route("/api/voice/command", methods=["POST"])
    @require_auth()
    def voice_command():
        data = request.json or {}
        command = str(data.get("command", "")).strip().lower()

        if not command:
            return jsonify({"msg": "Nenhum comando recebido"}), 400

        action = None
        target_state = {}

        if "ligar ventilador" in command or "ligar ventilacao" in command:
            action = "ventilador"
            target_state = {"ventilacao_ligada": True}
        elif "desligar ventilador" in command or "desligar ventilacao" in command:
            action = "ventilador"
            target_state = {"ventilacao_ligada": False}
        elif "ligar aquecedor" in command:
            action = "aquecedor"
            target_state = {"aquecedor_ligado": True}
        elif "desligar aquecedor" in command:
            action = "aquecedor"
            target_state = {"aquecedor_ligado": False}
        elif "luz" in command and "porcento" in command:
            try:
                import re

                match = re.search(r"(\d+)\s*porcento", command)
                if match:
                    nivel = int(match.group(1))
                    nivel = max(0, min(nivel, 100))
                    action = "luz_dimmer"
                    target_state = {"luz_dimmer": nivel}
            except Exception:
                pass

        if not action:
            return jsonify({"msg": "Comando não reconhecido ou suportado", "command": command}), 400

        action_perm = "device.manage"
        if action == "ventilador" or action == "aquecedor":
            action_perm = "device.power_on"
        elif action == "luz_dimmer":
            action_perm = "lighting.manage"

        if _guard_critical_action:
            ok, resp = _guard_critical_action("voice_command_control", permission=action_perm)
            if not ok:
                return resp

        estado_dispositivos.update(target_state)
        if _audit:
            _audit(
                "voice_command_executed",
                source="mobile_voice",
                details={"command": command, "action": action},
            )
        return jsonify(
            {"msg": "Comando executado", "action": action, "devices": estado_dispositivos}
        )


def _add_rules_routes(bp, deps):
    _require_permission = deps.get("require_permission")
    db = deps.get("db")
    AutomationRule = deps.get("AutomationRule")
    _guard_critical_action = deps.get("guard_critical_action")

    @bp.route("/api/rules", methods=["GET"])
    @require_auth()
    def get_rules():
        if _require_permission:
            ok, resp = _require_permission("monitor.read")
            if not ok:
                return resp
        if AutomationRule:
            rules = AutomationRule.query.all()
            return jsonify([r.to_dict() for r in rules])
        return jsonify([])

    @bp.route("/api/rules", methods=["POST"])
    @require_auth()
    def create_rule():
        if _guard_critical_action:
            ok, resp = _guard_critical_action("create_rule", permission="automation.manage")
            if not ok:
                return resp
        data = request.json or {}
        for k in [
            "name",
            "condition_variable",
            "condition_operator",
            "condition_value",
            "action_device",
            "action_state",
        ]:
            if data.get(k) and len(str(data[k])) > 100:
                return jsonify({"msg": "Input length limits exceeded"}), 400

        if AutomationRule and db:
            rule = AutomationRule(
                name=data.get("name"),
                condition_variable=data.get("condition_variable"),
                condition_operator=data.get("condition_operator"),
                condition_value=data.get("condition_value"),
                action_device=data.get("action_device"),
                action_state=data.get("action_state"),
                active=data.get("active", True),
            )
            db.session.add(rule)
            db.session.commit()
            return jsonify(rule.to_dict()), 201
        return jsonify({"msg": "Error"}), 500

    @bp.route("/api/rules/<int:rule_id>", methods=["DELETE"])
    @require_auth()
    def delete_rule(rule_id):
        if _guard_critical_action:
            ok, resp = _guard_critical_action("delete_rule", permission="automation.manage")
            if not ok:
                return resp
        if AutomationRule and db:
            rule = AutomationRule.query.get(rule_id)
            if not rule:
                return jsonify({"msg": "Regra não encontrada"}), 404
            db.session.delete(rule)
            db.session.commit()
            return jsonify({"msg": "Regra deletada"}), 200
        return jsonify({"msg": "Error"}), 500


def _add_push_routes(bp, deps):
    db = deps.get("db")
    _get_current_account = deps.get("get_current_account")

    @bp.route("/api/push-token", methods=["POST"])
    @require_auth()
    def register_push_token():
        data = request.json or {}
        token = str(data.get("token", "")).strip()
        _device_id = str(data.get("device_id", "")).strip()

        if not token:
            return jsonify({"msg": "token is required"}), 400

        if _get_current_account:
            acc = _get_current_account()
            if acc and db:
                if acc.push_token != token:
                    acc.push_token = token
                    db.session.commit()
        return jsonify({"msg": "Token registered/updated"})


def add_remaining_routes(bp, deps):
    _add_acoustic_routes(bp, deps)
    _add_voice_routes(bp, deps)
    _add_rules_routes(bp, deps)
    _add_push_routes(bp, deps)
