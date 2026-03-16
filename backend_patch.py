import re

with open('backend/app.py', 'r') as f:
    content = f.read()

# Make sure psutil is imported
if 'import psutil' not in content:
    content = content.replace('import json', 'import json\nimport psutil')

# Add Flask-SocketIO imports
if 'from flask_socketio import SocketIO, emit' not in content:
    content = content.replace('from flask_cors import CORS', 'from flask_cors import CORS\nfrom flask_socketio import SocketIO, emit')

# Initialize SocketIO
if 'socketio = SocketIO(' not in content:
    content = content.replace('db.init_app(app)', 'db.init_app(app)\nsocketio = SocketIO(app, cors_allowed_origins="*")')

# FCM Push function
fcm_fn = '''def _send_fcm_push(title, body):
    if SETTINGS.app_env == "development":
        LOGGER.info(f"[FCM MOCK] Push: {title} - {body}")
        return True
    try:
        token = os.getenv("FCM_SERVER_KEY")
        if not token: return False
        headers = {"Authorization": f"key={token}", "Content-Type": "application/json"}
        payload = {"to": "/topics/alerts", "notification": {"title": title, "body": body}}
        resp = requests.post("https://fcm.googleapis.com/fcm/send", json=payload, headers=headers, timeout=5)
        return resp.ok
    except Exception:
        return False
'''
if '_send_fcm_push' not in content:
    content = content.replace('def _enqueue_sync_item', fcm_fn + '\ndef _enqueue_sync_item')

# Modify _log_event to send push and socket.io emit
log_event_replace = '''        if str(level).lower() in {"high", "critical"}:
            sent = ALERT_PROVIDER.send(f"[{event_type}] {message}")
            if not sent:
                LOGGER.warning("Alert provider failed for event_type=%s", event_type)'''

log_event_new = '''        if str(level).lower() in {"high", "critical"}:
            sent = ALERT_PROVIDER.send(f"[{event_type}] {message}")
            if not sent:
                LOGGER.warning("Alert provider failed for event_type=%s", event_type)
            _send_fcm_push(f"ChikGuard Alerta: {event_type}", message)

        try:
            socketio.emit('new_alert', {
                'id': f"event-{row.id}",
                'tipo': event_type.upper(),
                'nivel': 'alto' if level == 'high' else 'medio' if level == 'medium' else 'baixo',
                'mensagem': message,
                'hora': _utcnow().strftime("%H:%M:%S"),
                'data': _utcnow().strftime("%d/%m/%Y")
            })
        except Exception:
            pass'''
content = content.replace(log_event_replace, log_event_new)

# Resolve ONNX models
resolve_onnx_old = '''_resolved_model_path = YOLO_SEG_MODEL_PATH if os.path.exists(YOLO_SEG_MODEL_PATH) else YOLO_MODEL_PATH
detector = ObjectDetector(model_path=_resolved_model_path)'''

resolve_onnx_new = '''def _resolve_model_path(base_path):
    onnx_path = base_path.replace('.pt', '.onnx')
    if os.path.exists(onnx_path):
        return onnx_path
    return base_path

_base_yolo = YOLO_SEG_MODEL_PATH if os.path.exists(YOLO_SEG_MODEL_PATH) else YOLO_MODEL_PATH
_resolved_model_path = _resolve_model_path(_base_yolo)
detector = ObjectDetector(model_path=_resolved_model_path)'''
content = content.replace(resolve_onnx_old, resolve_onnx_new)

# Update _analyze_behavior logic
behavior_old = '''    if dispersion_ratio < 0.12 and count >= 8:
        status = "FRIO_COMPORTAMENTAL"
        message = "Aviso: aves amontoadas. Possivel falha no aquecedor."
    elif edge_ratio > 0.45 and dispersion_ratio > 0.18 and count >= 8:
        status = "CALOR_COMPORTAMENTAL"
        message = "Aviso: aves nas bordas e dispersas. Possivel estresse termico por calor."'''

behavior_new = '''    temp_c = float(sensor_state.get("temperature_c", 25.0))
    if dispersion_ratio < 0.12 and count >= 8 and temp_c < 26.0:
        status = "FRIO_COMPORTAMENTAL"
        message = "Aviso: aves amontoadas e temp baixa. Risco de mortalidade por hipotermia. Falha provavel no aquecedor."
    elif edge_ratio > 0.45 and dispersion_ratio > 0.18 and count >= 8 and temp_c > 29.0:
        status = "CALOR_COMPORTAMENTAL"
        message = "Aviso: aves nas bordas e dispersas com alta temperatura. Risco de estresse termico e mortalidade. Verifique ventilacao."'''
content = content.replace(behavior_old, behavior_new)

# Hardware API endpoint
hw_endpoint = '''@app.route("/api/hardware", methods=["GET"])
def hardware_stats():
    if SETTINGS.app_env == "development":
        cpu = 45.2
        ram = 60.1
        disk = 40.5
    else:
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
        except Exception:
            cpu, ram, disk = 0.0, 0.0, 0.0
    return jsonify({
        "cpu_percent": cpu,
        "ram_percent": ram,
        "disk_percent": disk,
    })
'''
if 'def hardware_stats()' not in content:
    content = content.replace('if __name__ == "__main__":', hw_endpoint + '\nif __name__ == "__main__":')

# Add Telemetry worker and use socketio.run
telemetry_worker = '''def _telemetry_worker():
    while True:
        time.sleep(3)
        try:
            with app.app_context():
                ultima = Reading.query.order_by(Reading.id.desc()).first()
                with lock:
                    count = object_count
                payload = {
                    "temperatura_atual": ultima.temperatura if ultima else 0,
                    "status_atual": ultima.status if ultima else "INICIANDO",
                    "contagem_aves": count,
                    "dispositivos": estado_dispositivos,
                    "behavior": {
                        "status": behavior_state["status"],
                        "message": behavior_state["message"],
                    },
                    "sensors": {
                        "temperature_c": sensor_state["temperature_c"],
                        "humidity_pct": sensor_state["humidity_pct"],
                    },
                    "comfort_score": _comfort_score(),
                }
                socketio.emit('telemetry_update', payload)
        except Exception:
            pass
'''

if '_telemetry_worker' not in content:
    content = content.replace('if __name__ == "__main__":', telemetry_worker + '\nif __name__ == "__main__":')

if 'app.run(' in content:
    content = content.replace('app.run(host=SETTINGS.flask_host, port=SETTINGS.flask_port, debug=False)',
    '    telemetry_thread = threading.Thread(target=_telemetry_worker, daemon=True)\n    telemetry_thread.start()\n    socketio.run(app, host=SETTINGS.flask_host, port=SETTINGS.flask_port, debug=False, allow_unsafe_werkzeug=True)')

with open('backend/app.py', 'w') as f:
    f.write(content)
