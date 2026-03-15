from flask import Flask, jsonify, request, send_file, has_request_context
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, verify_jwt_in_request, get_jwt_identity
from database import (
    db,
    User,
    Reading,
    BirdSnapshot,
    BirdIdentity,
    BirdTrackPoint,
    EventLog,
    SensorReading,
    Batch,
    WeightEstimate,
    AcousticReading,
    ThermalAnomaly,
    EnergyUsageDaily,
    AuditLog,
    SyncQueueItem,
    BatchLogbook,
    Account,
    RolePermission,
)

import cv2
import numpy as np
import threading
import time
import os
import random
import json
import math
import ipaddress
from datetime import datetime, timedelta, timezone
from ultralytics import YOLO
from io import BytesIO
import smtplib
from email.message import EmailMessage
import io

from src.alerts.providers import build_alert_provider
from src.api.routes import create_api_blueprint
from src.core.config import load_settings
from src.core.logger import configure_logging
from src.plugins.manager import PluginManager

try:
    import requests
except Exception:
    requests = None

try:
    import psutil
except Exception:
    psutil = None

try:
    import librosa
except Exception:
    librosa = None

try:
    import soundfile as sf
except Exception:
    sf = None

try:
    import joblib
except Exception:
    joblib = None

try:
    import winsound
except Exception:
    winsound = None

try:
    from video_processor import VideoProcessor
except Exception:
    VideoProcessor = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
except Exception:
    canvas = None
    A4 = None

SETTINGS = load_settings()
LOGGER = configure_logging(SETTINGS.log_level)

MODO_DETECCAO = os.getenv("MODO_DETECCAO", "aves").strip().lower()
ACTIVE_CAMERA_ID = os.getenv("ACTIVE_CAMERA_ID", "galpao-1")

INFERENCE_IMGSZ = int(os.getenv("INFERENCE_IMGSZ", "960"))
DETECTION_CONF = float(os.getenv("DETECTION_CONF", "0.22"))
DETECTION_IOU = float(os.getenv("DETECTION_IOU", "0.45"))
MIN_BIRD_AREA_RATIO = float(os.getenv("MIN_BIRD_AREA_RATIO", "0.00003"))
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
YOLO_SEG_MODEL_PATH = os.getenv("YOLO_SEG_MODEL_PATH", "yolov8n-seg.pt")
BIRD_CLASS_NAME = os.getenv("BIRD_CLASS_NAME", "bird")
TRACKER_TYPE = os.getenv("TRACKER_TYPE", "bytetrack").strip().lower()
TRACKER_CONFIG = "botsort.yaml" if TRACKER_TYPE == "botsort" else "bytetrack.yaml"

BIRD_SNAPSHOT_SAVE_INTERVAL = int(os.getenv("BIRD_SNAPSHOT_SAVE_INTERVAL", "10"))
BIRD_LIVE_TTL_SEC = int(os.getenv("BIRD_LIVE_TTL_SEC", "4"))
REID_MAX_GAP_SEC = int(os.getenv("REID_MAX_GAP_SEC", "8"))
REID_MAX_DISTANCE_RATIO = float(os.getenv("REID_MAX_DISTANCE_RATIO", "0.12"))
TRACK_POINT_SAVE_INTERVAL = int(os.getenv("TRACK_POINT_SAVE_INTERVAL", "2"))
REID_APPEARANCE_MIN_SIM = float(os.getenv("REID_APPEARANCE_MIN_SIM", "0.18"))
REID_W_DIST = float(os.getenv("REID_W_DIST", "0.55"))
REID_W_SIZE = float(os.getenv("REID_W_SIZE", "0.20"))
REID_W_APPEAR = float(os.getenv("REID_W_APPEAR", "0.25"))

BEHAVIOR_ALERT_COOLDOWN_SEC = int(os.getenv("BEHAVIOR_ALERT_COOLDOWN_SEC", "120"))
IMMOBILITY_MIN_SEC = int(os.getenv("IMMOBILITY_MIN_SEC", "1800"))
IMMOBILITY_MOVE_PX = int(os.getenv("IMMOBILITY_MOVE_PX", "12"))
IMMOBILITY_ALERT_COOLDOWN_SEC = int(os.getenv("IMMOBILITY_ALERT_COOLDOWN_SEC", "300"))
CARCASS_STILL_SECONDS = int(os.getenv("CARCASS_STILL_SECONDS", "1800"))

SENSOR_SAVE_INTERVAL = int(os.getenv("SENSOR_SAVE_INTERVAL", "30"))
SENSOR_ALERT_COOLDOWN_SEC = int(os.getenv("SENSOR_ALERT_COOLDOWN_SEC", "300"))

INTRUSION_START_HOUR = int(os.getenv("INTRUSION_START_HOUR", "0"))
INTRUSION_END_HOUR = int(os.getenv("INTRUSION_END_HOUR", "5"))
INTRUSION_COOLDOWN_SEC = int(os.getenv("INTRUSION_COOLDOWN_SEC", "180"))

WEIGHT_SAVE_INTERVAL = int(os.getenv("WEIGHT_SAVE_INTERVAL", "600"))
WEIGHT_CALIBRATION_G_PER_SQRT_PX = float(os.getenv("WEIGHT_CALIBRATION_G_PER_SQRT_PX", "1.85"))
THERMAL_ANOMALY_COOLDOWN_SEC = int(os.getenv("THERMAL_ANOMALY_COOLDOWN_SEC", "180"))
ACOUSTIC_SAVE_INTERVAL = int(os.getenv("ACOUSTIC_SAVE_INTERVAL", "60"))

VENTILACAO_POWER_KW = float(os.getenv("VENTILACAO_POWER_KW", "0.35"))
AQUECEDOR_POWER_KW = float(os.getenv("AQUECEDOR_POWER_KW", "1.80"))
ENERGY_TARIFF_PER_KWH = float(os.getenv("ENERGY_TARIFF_PER_KWH", "0.95"))
CAMERA_DISTANCE_M = float(os.getenv("CAMERA_DISTANCE_M", "2.2"))
VIRTUAL_SCALE_CM_PER_PX_AT_1M = float(os.getenv("VIRTUAL_SCALE_CM_PER_PX_AT_1M", "0.09"))

SYNC_PUSH_INTERVAL_SEC = int(os.getenv("SYNC_PUSH_INTERVAL_SEC", "45"))
CLOUD_SYNC_URL = os.getenv("CLOUD_SYNC_URL", "").strip()
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()
WEATHER_LAT = os.getenv("OPENWEATHER_LAT", "").strip()
WEATHER_LON = os.getenv("OPENWEATHER_LON", "").strip()
WEATHER_CHECK_INTERVAL_SEC = int(os.getenv("WEATHER_CHECK_INTERVAL_SEC", "1800"))
WEATHER_COLD_FRONT_C = float(os.getenv("WEATHER_COLD_FRONT_C", "5.0"))
CAMERA_FAIL_THRESHOLD = int(os.getenv("CAMERA_FAIL_THRESHOLD", "25"))
CAMERA_REOPEN_INTERVAL_SEC = float(os.getenv("CAMERA_REOPEN_INTERVAL_SEC", "3.0"))
CAMERA_TARGET_FPS = float(os.getenv("CAMERA_TARGET_FPS", "30"))
STREAM_TARGET_FPS = float(os.getenv("STREAM_TARGET_FPS", "30"))
STREAM_JPEG_QUALITY = int(os.getenv("STREAM_JPEG_QUALITY", "82"))
TAMPER_ALERT_COOLDOWN_SEC = int(os.getenv("TAMPER_ALERT_COOLDOWN_SEC", "180"))
TAMPER_SENSOR_STALE_SEC = int(os.getenv("TAMPER_SENSOR_STALE_SEC", "180"))
TAMPER_DARK_MEAN_THRESHOLD = float(os.getenv("TAMPER_DARK_MEAN_THRESHOLD", "24.0"))
TAMPER_LOW_TEXTURE_STD_THRESHOLD = float(os.getenv("TAMPER_LOW_TEXTURE_STD_THRESHOLD", "8.0"))
TAMPER_FREEZE_DIFF_THRESHOLD = float(os.getenv("TAMPER_FREEZE_DIFF_THRESHOLD", "1.2"))
TAMPER_FREEZE_MIN_FRAMES = int(os.getenv("TAMPER_FREEZE_MIN_FRAMES", "45"))
CRITICAL_ALLOWED_CIDRS = [x.strip() for x in os.getenv("CRITICAL_ALLOWED_CIDRS", "").split(",") if x.strip()]
LOGIN_RATE_WINDOW_SEC = int(os.getenv("LOGIN_RATE_WINDOW_SEC", "300"))
LOGIN_RATE_MAX_ATTEMPTS = int(os.getenv("LOGIN_RATE_MAX_ATTEMPTS", "10"))
COUGH_MODEL_PATH = os.getenv("COUGH_MODEL_PATH", os.path.join(os.path.dirname(__file__), "models", "cough_classifier.joblib"))
COUGH_MODEL_FEATURES = int(os.getenv("COUGH_MODEL_FEATURES", "48"))
SIM_VIDEO_PATH = os.getenv("SIM_VIDEO_PATH", "video_granja.mp4").strip()
VIEWER_USERNAME = os.getenv("VIEWER_USERNAME", "").strip()
VIEWER_PASSWORD = os.getenv("VIEWER_PASSWORD", "").strip()

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
HEATMAP_DIR = os.path.join(REPORTS_DIR, "heatmaps")
os.makedirs(HEATMAP_DIR, exist_ok=True)
STREAM_JPEG_QUALITY = max(40, min(STREAM_JPEG_QUALITY, 95))
STREAM_FRAME_INTERVAL_SEC = 1.0 / STREAM_TARGET_FPS if STREAM_TARGET_FPS > 0 else 0.0


def _configure_camera_capture(cap):
    if cap is None:
        return
    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        if CAMERA_TARGET_FPS > 0:
            cap.set(cv2.CAP_PROP_FPS, CAMERA_TARGET_FPS)
        # Keep capture latency low for real-time detection/tracking.
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass


class ObjectDetector:
    def __init__(self, model_path="yolov8n.pt"):
        self.yolo_loaded = False
        self.model = None
        self.supports_segmentation = False
        try:
            self.model = YOLO(model_path)
            self.yolo_loaded = True
            LOGGER.info("Model '%s' loaded.", model_path)
            self.model.predict(np.zeros((480, 640, 3)), verbose=False)
            LOGGER.info("Model warmed up.")
            try:
                # Seg models expose masks at inference time.
                dummy = self.model.predict(np.zeros((256, 256, 3), dtype=np.uint8), verbose=False)
                self.supports_segmentation = bool(dummy and getattr(dummy[0], "masks", None) is not None)
            except Exception:
                self.supports_segmentation = False
        except Exception as exc:
            LOGGER.exception("Error loading Ultralytics model: %s", exc)

    def detect(self, frame):
        if not self.yolo_loaded:
            return []

        results = self.model.track(
            frame,
            verbose=False,
            persist=True,
            tracker=TRACKER_CONFIG,
            conf=DETECTION_CONF,
            iou=DETECTION_IOU,
            imgsz=INFERENCE_IMGSZ,
        )

        result = results[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []

        xyxy = boxes.xyxy.cpu().numpy().astype(int)
        class_ids = boxes.cls.cpu().numpy().astype(int)
        confidences = boxes.conf.cpu().numpy()
        track_ids = (
            boxes.id.cpu().numpy().astype(int)
            if boxes.id is not None
            else np.full(len(xyxy), -1, dtype=int)
        )
        mask_areas = np.zeros(len(xyxy), dtype=np.float32)
        if getattr(result, "masks", None) is not None and getattr(result.masks, "data", None) is not None:
            try:
                mask_stack = result.masks.data.cpu().numpy()
                for i in range(min(len(mask_stack), len(mask_areas))):
                    mask_areas[i] = float(np.sum(mask_stack[i] > 0.5))
                self.supports_segmentation = True
            except Exception:
                pass

        detections = []
        for i in range(len(xyxy)):
            detections.append(
                {
                    "box": xyxy[i],
                    "class_id": int(class_ids[i]),
                    "confidence": float(confidences[i]),
                    "track_id": int(track_ids[i]),
                    "mask_area_px": float(mask_areas[i]) if i < len(mask_areas) else 0.0,
                }
            )
        return detections


class RespiratoryAudioClassifier:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.loaded = False
        self.last_error = None
        if joblib is None or librosa is None:
            self.last_error = "joblib_or_librosa_unavailable"
            return
        try:
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                self.loaded = True
            else:
                self.last_error = "model_file_not_found"
        except Exception as exc:
            self.last_error = str(exc)

    def _extract_features(self, y, sr):
        # Fixed-size statistical audio descriptor for cough/stress classifiers.
        y = np.asarray(y, dtype=np.float32).flatten()
        if y.size == 0:
            return None
        if sr <= 0:
            sr = 16000
        if y.size < sr:
            y = np.pad(y, (0, sr - y.size))
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
        spec_cent = librosa.feature.spectral_centroid(y=y, sr=sr)
        spec_bw = librosa.feature.spectral_bandwidth(y=y, sr=sr)
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
        zcr = librosa.feature.zero_crossing_rate(y)
        rms = librosa.feature.rms(y=y)

        feats = []
        for mat in (mfcc, spec_cent, spec_bw, rolloff, zcr, rms):
            feats.append(float(np.mean(mat)))
            feats.append(float(np.std(mat)))
            feats.append(float(np.min(mat)))
            feats.append(float(np.max(mat)))
        vec = np.asarray(feats, dtype=np.float32)
        if vec.size < COUGH_MODEL_FEATURES:
            vec = np.pad(vec, (0, COUGH_MODEL_FEATURES - vec.size))
        elif vec.size > COUGH_MODEL_FEATURES:
            vec = vec[:COUGH_MODEL_FEATURES]
        return vec.reshape(1, -1)

    def classify(self, y, sr):
        if not self.loaded or self.model is None:
            return None
        try:
            X = self._extract_features(y, sr)
            if X is None:
                return None
            cough_prob = None
            stress_prob = None
            if hasattr(self.model, "predict_proba"):
                proba = self.model.predict_proba(X)
                # Convention: binary classifier with positive class = cough.
                if isinstance(proba, list):
                    arr = np.asarray(proba[0], dtype=np.float32).reshape(-1)
                else:
                    arr = np.asarray(proba, dtype=np.float32).reshape(-1)
                if arr.size >= 2:
                    cough_prob = float(arr[-1])
                else:
                    cough_prob = float(arr[0])
            elif hasattr(self.model, "predict"):
                pred = self.model.predict(X)
                cough_prob = float(np.asarray(pred).reshape(-1)[0])
            if cough_prob is None:
                return None
            stress_prob = min(1.0, max(0.0, (cough_prob * 0.6) + random.uniform(0.05, 0.22)))
            respiratory_health = max(0.0, min(100.0, 100.0 - ((cough_prob * 70.0) + (stress_prob * 30.0))))
            return {
                "respiratory_health_index": round(float(respiratory_health), 2),
                "cough_index": round(float(cough_prob * 100.0), 2),
                "stress_audio_index": round(float(stress_prob * 100.0), 2),
                "source": "trained_model",
            }
        except Exception as exc:
            self.last_error = str(exc)
            return None


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SETTINGS.database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = SETTINGS.jwt_secret_key

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
db.init_app(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
ALERT_PROVIDER = build_alert_provider(SETTINGS)
PLUGINS_ROOT = os.getenv("PLUGINS_DIR", os.path.join(os.path.dirname(__file__), "plugins"))
PLUGIN_MANAGER = PluginManager(plugins_root=PLUGINS_ROOT, logger=LOGGER)
PLUGIN_MANAGER.load_all({"logger": LOGGER, "settings": SETTINGS})


def _safe_json(value):
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return json.dumps({"raw": str(value)})


def _utcnow():
    # Python is deprecating naive utcnow(); keep UTC source but store naive UTC in DB.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _log_event(event_type, level, message, metadata=None, camera_id=ACTIVE_CAMERA_ID):
    try:
        with app.app_context():
            row = EventLog(
                camera_id=camera_id,
                event_type=event_type,
                level=level,
                message=message,
                metadata_json=_safe_json(metadata or {}),
            )
            db.session.add(row)
            db.session.commit()
            _enqueue_sync_item("event_log", row.to_dict())
        if str(level).lower() in {"high", "critical"}:
            sent = ALERT_PROVIDER.send(f"[{event_type}] {message}")
            if not sent:
                LOGGER.warning("Alert provider failed for event_type=%s", event_type)

        event_payload = {
            "camera_id": camera_id,
            "event_type": event_type,
            "level": level,
            "message": message,
            "metadata": metadata or {},
            "timestamp": _utcnow().isoformat()
        }

        # Enviar via WebSocket instantaneamente
        try:
            socketio.emit("new_alert", event_payload)
        except Exception as ws_exc:
            LOGGER.warning("Failed to emit WebSocket event: %s", ws_exc)

        PLUGIN_MANAGER.emit_event("event_log", event_payload)
    except Exception as exc:
        LOGGER.exception("[EVENT] failed to persist '%s': %s", event_type, exc)


def _enqueue_sync_item(item_type, payload):
    _enqueue_sync_items_bulk(item_type, [payload])


def _enqueue_sync_items_bulk(item_type, payloads):
    try:
        with app.app_context():
            rows = [
                SyncQueueItem(item_type=item_type, payload_json=_safe_json(p), status="pending")
                for p in payloads
            ]
            db.session.bulk_save_objects(rows)
            db.session.commit()
    except Exception as exc:
        LOGGER.exception("[SYNC] bulk enqueue failed: %s", exc)


def _request_actor():
    actor = "system"
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            actor = str(identity)
    except Exception:
        actor = "system"
    return actor


def _request_ip():
    try:
        return str(request.headers.get("X-Forwarded-For", request.remote_addr) or "").split(",")[0].strip()
    except Exception:
        return ""


def _ip_allowed_for_critical(ip_str):
    if not CRITICAL_ALLOWED_CIDRS:
        return True
    try:
        ip_obj = ipaddress.ip_address(ip_str)
    except Exception:
        return False
    for cidr in CRITICAL_ALLOWED_CIDRS:
        try:
            if ip_obj in ipaddress.ip_network(cidr, strict=False):
                return True
        except Exception:
            continue
    return False


def _guard_critical_action(action_name, permission=None):
    try:
        verify_jwt_in_request(optional=False)
    except Exception:
        _audit("critical_action_denied_no_jwt", source="security", details={"action": action_name})
        return False, (jsonify({"msg": "JWT obrigatorio para comando critico"}), 401)
    ip = _request_ip()
    if not _ip_allowed_for_critical(ip):
        _audit("critical_action_denied_geofence", source="security", details={"action": action_name, "ip": ip})
        return False, (jsonify({"msg": "Acesso bloqueado por geofencing"}), 403)
    if permission:
        ok_perm, resp_perm = _require_permission(permission)
        if not ok_perm:
            _audit("critical_action_denied_permission", source="security", details={"action": action_name, "permission": permission})
            return False, resp_perm
    return True, None


def _get_current_account():
    try:
        verify_jwt_in_request(optional=True)
        username = get_jwt_identity()
    except Exception:
        username = None
    if not username:
        return None
    return Account.query.filter_by(username=str(username)).first()


def _account_has_permission(account, permission):
    if account is None or not account.active:
        return False
    rows = RolePermission.query.filter_by(role=account.role, allowed=True).all()
    perms = {r.permission for r in rows}
    if "*" in perms:
        return True
    return permission in perms


def _require_permission(permission):
    account = _get_current_account()
    if not _account_has_permission(account, permission):
        _audit("permission_denied", source="security", details={"permission": permission, "actor": account.username if account else None})
        return False, (jsonify({"msg": f"Permissao negada: {permission}"}), 403)
    return True, None


def _audit(action, source="backend", details=None, actor=None):
    try:
        actor_name = actor or _request_actor()
        ip_value = str(request.remote_addr) if has_request_context() else None
        row = AuditLog(
            actor=actor_name,
            action=action,
            source=source,
            ip=ip_value,
            details_json=_safe_json(details or {}),
        )
        with app.app_context():
            db.session.add(row)
            db.session.commit()
            payload = row.to_dict()
        _enqueue_sync_item("audit_log", payload)
    except Exception as exc:
        LOGGER.exception("[AUDIT] failed: %s", exc)


def _class_name_by_id(class_id):
    names = detector.model.names if detector and detector.model is not None else {}
    if isinstance(names, dict):
        return str(names.get(class_id, ""))
    if isinstance(names, list) and 0 <= class_id < len(names):
        return str(names[class_id])
    return ""


def _box_center_area(box):
    x1, y1, x2, y2 = [int(v) for v in box]
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    area = max(1, (x2 - x1) * (y2 - y1))
    return cx, cy, area


def _extract_appearance_signature(frame, box):
    x1, y1, x2, y2 = [int(v) for v in box]
    h, w = frame.shape[:2]
    x1 = max(0, min(x1, w - 1))
    x2 = max(0, min(x2, w))
    y1 = max(0, min(y1, h - 1))
    y2 = max(0, min(y2, h))
    if x2 <= x1 or y2 <= y1:
        return None
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return None
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [12, 12], [0, 180, 0, 256])
    hist = cv2.normalize(hist, hist).flatten()
    return hist.astype(np.float32)


def _appearance_similarity(hist_a, hist_b):
    if hist_a is None or hist_b is None:
        return 0.0
    score = float(cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL))
    if np.isnan(score):
        return 0.0
    return max(0.0, min(1.0, (score + 1.0) / 2.0))


def _estimate_bird_temp_proxy(gray_frame, box, ambient_temp):
    x1, y1, x2, y2 = box
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(gray_frame.shape[1], x2)
    y2 = min(gray_frame.shape[0], y2)
    if x2 <= x1 or y2 <= y1:
        return round(float(ambient_temp), 2)
    roi = gray_frame[y1:y2, x1:x2]
    if roi.size == 0:
        return round(float(ambient_temp), 2)
    local_brightness = float(np.mean(roi))
    adjustment = ((local_brightness / 255.0) - 0.5) * 2.5
    return round(float(ambient_temp + adjustment), 2)


with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
        if not admin_password:
            raise RuntimeError("ADMIN_PASSWORD environment variable is not set. Cannot create default admin user securely.")
        hashed = bcrypt.generate_password_hash(admin_password).decode("utf-8")
        db.session.add(User(username="admin", password=hashed))
        db.session.commit()
    if not Account.query.filter_by(username="admin").first():
        legacy_admin = User.query.filter_by(username="admin").first()
        if legacy_admin is not None:
            admin_hash = legacy_admin.password
        else:
            admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
            if not admin_password:
                raise RuntimeError("ADMIN_PASSWORD environment variable is not set. Cannot create default admin account securely.")
            admin_hash = bcrypt.generate_password_hash(admin_password).decode("utf-8")
        db.session.add(Account(username="admin", password_hash=admin_hash, role="admin", active=True))
        db.session.commit()
    if VIEWER_USERNAME and VIEWER_PASSWORD and not Account.query.filter_by(username=VIEWER_USERNAME).first():
        viewer_hash = bcrypt.generate_password_hash(VIEWER_PASSWORD).decode("utf-8")
        db.session.add(Account(username=VIEWER_USERNAME, password_hash=viewer_hash, role="viewer", active=True))
        db.session.commit()

    default_perms = {
        "admin": [
            "*"
        ],
        "operator": [
            "monitor.read",
            "alerts.read",
            "device.power_on",
            "lighting.manage",
            "voice.command",
            "logbook.write",
        ],
        "viewer": [
            "monitor.read",
            "alerts.read",
        ],
    }
    for role, perms in default_perms.items():
        for perm in perms:
            exists = RolePermission.query.filter_by(role=role, permission=perm).first()
            if exists is None:
                db.session.add(RolePermission(role=role, permission=perm, allowed=True))
    db.session.commit()

    if not Batch.query.filter_by(camera_id=ACTIVE_CAMERA_ID, active=True).first():
        db.session.add(
            Batch(
                camera_id=ACTIVE_CAMERA_ID,
                name="Lote inicial",
                start_date=_utcnow(),
                active=True,
                notes="Criado automaticamente",
            )
        )
        db.session.commit()


CAMERA_INDEX = SETTINGS.camera_index
global_frame = None
fps_last_time = 0.0
db_last_save_time = 0.0
last_bird_snapshot_save_time = 0.0
last_track_point_save_time = 0.0
lock = threading.Lock()
object_count = 0
APP_START_TIME = time.time()

_resolved_model_path = YOLO_SEG_MODEL_PATH if os.path.exists(YOLO_SEG_MODEL_PATH) else YOLO_MODEL_PATH

# Prioritize ONNX models for TensorRT/ONNX acceleration if available
_onnx_seg_path = YOLO_SEG_MODEL_PATH.replace(".pt", ".onnx")
_onnx_det_path = YOLO_MODEL_PATH.replace(".pt", ".onnx")

if os.path.exists(_onnx_seg_path):
    _resolved_model_path = _onnx_seg_path
    LOGGER.info(f"Usando modelo ONNX acelerado (Seg): {_resolved_model_path}")
elif os.path.exists(_onnx_det_path):
    _resolved_model_path = _onnx_det_path
    LOGGER.info(f"Usando modelo ONNX acelerado (Det): {_resolved_model_path}")

detector = ObjectDetector(model_path=_resolved_model_path)
audio_classifier = RespiratoryAudioClassifier(COUGH_MODEL_PATH)
live_birds = {}
track_to_bird_uid = {}
bird_last_state = {}
next_bird_uid = 1

behavior_state = {
    "status": "NORMAL",
    "message": "Aguardando deteccao",
    "dispersion_ratio": 0.0,
    "edge_ratio": 0.0,
    "count": 0,
    "updated_at": time.time(),
    "last_alert_ts": 0.0,
}

immobility_state = {}
intrusion_state = {"last_alert_ts": 0.0}
carcass_state = {"uids": set(), "items": [], "last_alert_ts": 0.0}
last_temp_emergency_notification_ts = 0.0

camera_registry = [
    {"camera_id": ACTIVE_CAMERA_ID, "source": f"webcam:{CAMERA_INDEX}", "enabled": True}
]

estado_dispositivos = {
    "ventilacao": False,
    "aquecedor": False,
    "modo_automatico": False,
    "luz_intensidade_pct": 0,
    "camera_id": ACTIVE_CAMERA_ID,
}

auto_config = {
    "fan_on_temp": 32.0,
    "fan_off_temp": 31.0,
    "heater_on_temp": 24.0,
    "heater_off_temp": 25.0,
    "use_batch_curve": True,
}

sensor_state = {
    "temperature_c": 28.0,
    "humidity_pct": 60.0,
    "ammonia_ppm": 8.0,
    "feed_level_pct": 100.0,
    "water_level_pct": 100.0,
    "source": "simulated",
    "updated_at": time.time(),
}

sensor_thresholds = {
    "humidity_low": 45.0,
    "humidity_high": 75.0,
    "ammonia_high": 20.0,
    "feed_low": 30.0,
    "water_low": 30.0,
}
sensor_alert_state = {}

weight_state = {
    "avg_weight_g": 0.0,
    "ideal_weight_g": 0.0,
    "count": 0,
    "confidence": 0.0,
    "updated_at": 0.0,
}
last_weight_save_ts = 0.0
last_thermal_alert_ts = 0.0

acoustic_state = {
    "respiratory_health_index": 100.0,
    "cough_index": 0.0,
    "stress_audio_index": 0.0,
    "source": "simulated",
    "updated_at": 0.0,
}
last_acoustic_save_ts = 0.0

energy_runtime_state = {
    "last_tick": time.time(),
    "ventilacao_seconds_today": 0.0,
    "aquecedor_seconds_today": 0.0,
}

weather_state = {
    "loaded": False,
    "next_night_min_c": None,
    "preheat_recommended": False,
    "message": "Sem previsao carregada",
    "updated_at": 0.0,
}
tamper_state = {
    "last_alert_ts": 0.0,
    "dark_frames": 0,
    "freeze_frames": 0,
    "last_causes": [],
    "alerts_count": 0,
    "sensor_stale": False,
}
last_visible_frame = None
_tamper_prev_gray = None
login_attempt_state = {}

last_weekly_report_key = None

hardware_state = {
    "cpu_usage_pct": 0.0,
    "ram_usage_pct": 0.0,
    "disk_usage_pct": 0.0,
    "cpu_temp_c": 0.0,
    "is_mocked": True,
    "last_update": 0.0
}


def _hardware_monitor_worker():
    while True:
        try:
            now = time.time()
            if psutil is not None and not os.getenv("ENV", "").strip().lower() == "development":
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent

                # Temperatura da CPU (se disponivel no psutil, em Windows 11 pode falhar/estar vazio)
                temp = 0.0
                has_real_temp = False
                if hasattr(psutil, "sensors_temperatures"):
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for name, entries in temps.items():
                            for entry in entries:
                                if entry.current:
                                    temp = max(temp, entry.current)
                                    has_real_temp = True

                if not has_real_temp:
                    temp = 45.0 + random.uniform(-2, 3) # Mock the temperature if unavailable

                hardware_state.update({
                    "cpu_usage_pct": cpu,
                    "ram_usage_pct": ram,
                    "disk_usage_pct": disk,
                    "cpu_temp_c": round(temp, 1),
                    "is_mocked": False,
                    "last_update": now
                })
            else:
                # Mock para desenvolvimento (ex: Windows 11 / sem acesso ao hardware real do pi)
                hardware_state.update({
                    "cpu_usage_pct": round(random.uniform(15.0, 35.0), 1),
                    "ram_usage_pct": round(random.uniform(40.0, 60.0), 1),
                    "disk_usage_pct": 45.5,
                    "cpu_temp_c": round(random.uniform(40.0, 50.0), 1),
                    "is_mocked": True,
                    "last_update": now
                })

            # Emitir métricas de hardware via websocket
            try:
                socketio.emit("hardware_update", hardware_state)
            except Exception as ws_exc:
                LOGGER.warning("Failed to emit hardware stats: %s", ws_exc)

            time.sleep(15) # Atualiza a cada 15 segundos
        except Exception as exc:
            LOGGER.exception("[HARDWARE] monitor error: %s", exc)
            time.sleep(30)


def _init_bird_uid_counter():
    global next_bird_uid
    with app.app_context():
        max_identity = db.session.query(db.func.max(BirdIdentity.bird_uid)).scalar()
        max_snapshot = db.session.query(db.func.max(BirdSnapshot.bird_uid)).scalar()
    max_seen = max(filter(lambda v: v is not None, [max_identity, max_snapshot]), default=0)
    next_bird_uid = int(max_seen) + 1


def _allocate_new_bird_uid():
    global next_bird_uid
    uid = int(next_bird_uid)
    next_bird_uid += 1
    return uid


def _resolve_stable_bird_uid(track_id, box, now_ts, frame, used_uids):
    if track_id in track_to_bird_uid:
        uid = int(track_to_bird_uid[track_id])
        if uid not in used_uids:
            return uid

    frame_h, frame_w = frame.shape[:2]
    max_dist = max(20, int(min(frame_w, frame_h) * REID_MAX_DISTANCE_RATIO))
    cx, cy, area = _box_center_area(box)
    current_hist = _extract_appearance_signature(frame, box)

    best_uid = None
    best_score = None
    for uid, state in bird_last_state.items():
        if uid in used_uids:
            continue
        gap = now_ts - float(state["last_seen"])
        if gap > REID_MAX_GAP_SEC:
            continue

        lx, ly = state["center"]
        vx = float(state.get("vx", 0.0))
        vy = float(state.get("vy", 0.0))
        px = lx + (vx * gap)
        py = ly + (vy * gap)
        larea = max(1, int(state["area"]))

        dist = abs(cx - px) + abs(cy - py)
        if dist > max_dist:
            continue

        area_ratio = float(area) / float(larea)
        if area_ratio < 0.4 or area_ratio > 2.5:
            continue

        appear_sim = _appearance_similarity(current_hist, state.get("appearance"))
        if appear_sim < REID_APPEARANCE_MIN_SIM:
            continue

        dist_norm = min(1.0, float(dist) / float(max_dist))
        size_norm = min(1.0, abs(area_ratio - 1.0))
        appear_norm = 1.0 - appear_sim
        score = (REID_W_DIST * dist_norm) + (REID_W_SIZE * size_norm) + (REID_W_APPEAR * appear_norm)
        if best_score is None or score < best_score:
            best_score = score
            best_uid = int(uid)

    if best_uid is None:
        best_uid = _allocate_new_bird_uid()

    track_to_bird_uid[track_id] = best_uid
    return best_uid

def _active_batch(camera_id):
    with app.app_context():
        return (
            Batch.query.filter_by(camera_id=camera_id, active=True)
            .order_by(Batch.id.desc())
            .first()
        )


def _ideal_temp_for_age_day(age_day):
    if age_day <= 7:
        return 32.0
    if age_day <= 14:
        return 30.0
    if age_day <= 21:
        return 27.0
    if age_day <= 28:
        return 24.0
    return 22.0


def _temperature_targets(camera_id):
    fan_on = auto_config["fan_on_temp"]
    fan_off = auto_config["fan_off_temp"]
    heater_on = auto_config["heater_on_temp"]
    heater_off = auto_config["heater_off_temp"]
    target = None
    age_day = None

    if auto_config.get("use_batch_curve", True):
        batch = _active_batch(camera_id)
        if batch is not None:
            age_day = max(1, (_utcnow().date() - batch.start_date.date()).days + 1)
            target = _ideal_temp_for_age_day(age_day)
            heater_on = max(16.0, target - 0.5)
            heater_off = max(16.0, target + 0.2)
            fan_on = min(40.0, target + 2.0)
            fan_off = min(40.0, target + 1.0)

    return {
        "fan_on_temp": fan_on,
        "fan_off_temp": fan_off,
        "heater_on_temp": heater_on,
        "heater_off_temp": heater_off,
        "target_temp": target,
        "batch_age_day": age_day,
    }


def _ideal_weight_for_age_day(age_day):
    # Curva de referência simplificada (broiler), em gramas.
    curve = {
        1: 45, 7: 185, 14: 470, 21: 950, 28: 1550, 35: 2300, 42: 2950
    }
    keys = sorted(curve.keys())
    if age_day <= keys[0]:
        return float(curve[keys[0]])
    if age_day >= keys[-1]:
        return float(curve[keys[-1]])
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        if a <= age_day <= b:
            ratio = (age_day - a) / float(max(1, b - a))
            return float(curve[a] + ((curve[b] - curve[a]) * ratio))
    return float(curve[keys[-1]])


def _estimate_weight_from_live_birds(frame_shape):
    now = time.time()
    with lock:
        birds = [v for v in live_birds.values() if (now - float(v["last_seen"])) <= BIRD_LIVE_TTL_SEC]
    if not birds:
        return None

    fh, fw = frame_shape[:2]
    weights = []
    for bird in birds:
        x1, y1, x2, y2 = bird["box"]
        bw = max(1, (x2 - x1))
        bh = max(1, (y2 - y1))
        bbox_area = float(bw * bh)
        seg_area = float(bird.get("mask_area_px", 0.0))
        area_px = seg_area if seg_area > 0 else bbox_area

        # Virtual ruler:
        # physical_size_cm ~= px * scale(1m) * distance_m
        scale = VIRTUAL_SCALE_CM_PER_PX_AT_1M * max(0.5, CAMERA_DISTANCE_M)
        body_area_cm2 = max(1.0, area_px * (scale ** 2))
        # Approximate mass relation from projected body area.
        base_weight = WEIGHT_CALIBRATION_G_PER_SQRT_PX * math.sqrt(body_area_cm2 * 100.0)
        # Minor perspective correction using vertical position.
        cy = (y1 + y2) / 2.0
        perspective = 0.92 + (0.16 * (cy / float(max(1, fh))))
        weights.append(base_weight * perspective)
    if not weights:
        return None

    avg_weight_from_area = float(sum(weights) / len(weights))
    batch = _active_batch(ACTIVE_CAMERA_ID)
    age_day = max(1, (_utcnow().date() - batch.start_date.date()).days + 1) if batch else 21
    ideal = _ideal_weight_for_age_day(age_day)

    # Blend between area-based estimate and age-based expected curve.
    estimated = (0.7 * avg_weight_from_area) + (0.3 * ideal)
    confidence = min(0.97, max(0.45, 0.52 + (len(weights) / 120.0)))
    return {
        "avg_weight_g": round(float(estimated), 1),
        "ideal_weight_g": round(float(ideal), 1),
        "count": int(len(weights)),
        "confidence": round(float(confidence), 3),
        "age_day": int(age_day),
    }


def _persist_weight_estimate(frame_shape):
    global last_weight_save_ts
    now = time.time()
    data = _estimate_weight_from_live_birds(frame_shape)
    if data is None:
        return
    weight_state.update(
        {
            "avg_weight_g": data["avg_weight_g"],
            "ideal_weight_g": data["ideal_weight_g"],
            "count": data["count"],
            "confidence": data["confidence"],
            "updated_at": now,
        }
    )
    if now - last_weight_save_ts < WEIGHT_SAVE_INTERVAL:
        return
    with app.app_context():
        row = WeightEstimate(
            camera_id=ACTIVE_CAMERA_ID,
            avg_weight_g=data["avg_weight_g"],
            ideal_weight_g=data["ideal_weight_g"],
            flock_count=data["count"],
            confidence=data["confidence"],
            source="vision_estimate",
        )
        db.session.add(row)
        db.session.commit()
        _enqueue_sync_item("weight_estimate", row.to_dict())
    last_weight_save_ts = now


def _sector_from_point(x, y, frame_shape):
    h, w = frame_shape[:2]
    if w <= 0 or h <= 0:
        return "A"
    col = min(2, int((x / float(w)) * 3))
    row = min(2, int((y / float(h)) * 3))
    return f"{chr(ord('A') + row)}{col + 1}"


def _detect_thermal_anomalies(gray_frame, ambient_temp, frame_shape):
    global last_thermal_alert_ts
    now = time.time()
    with lock:
        birds_items = list(live_birds.items())
    anomalies = []
    for bird_uid, data in birds_items:
        box = data["box"]
        est_temp = _estimate_bird_temp_proxy(gray_frame, box, ambient_temp)
        x1, y1, x2, y2 = box
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        diff = est_temp - float(ambient_temp)
        if diff >= 8.0:
            kind = "fever_suspected"
        elif diff <= -6.0:
            kind = "hypothermia_or_mortality"
        else:
            continue
        anomalies.append(
            {
                "bird_uid": int(bird_uid),
                "kind": kind,
                "estimated_temp_c": round(float(est_temp), 2),
                "ambient_temp_c": round(float(ambient_temp), 2),
                "sector": _sector_from_point(cx, cy, frame_shape),
                "x": cx,
                "y": cy,
            }
        )

    if not anomalies:
        return

    with app.app_context():
        rows = [ThermalAnomaly(camera_id=ACTIVE_CAMERA_ID, **a) for a in anomalies[:30]]
        db.session.bulk_save_objects(rows)
        db.session.commit()
        _enqueue_sync_items_bulk("thermal_anomaly", [r.to_dict() for r in rows])

    if (now - last_thermal_alert_ts) >= THERMAL_ANOMALY_COOLDOWN_SEC:
        last_thermal_alert_ts = now
        sectors = sorted(list({a["sector"] for a in anomalies if a.get("sector")}))
        _log_event(
            event_type="thermal_anomaly_alert",
            level="high",
            message=f"Aves com temperatura anomala: {len(anomalies)} detectadas em {', '.join(sectors)}",
            metadata={"count": len(anomalies), "sectors": sectors},
        )


def _simulate_acoustic_analysis():
    global last_acoustic_save_ts
    now = time.time()
    if now - last_acoustic_save_ts < ACOUSTIC_SAVE_INTERVAL:
        return

    ammonia_factor = min(35.0, float(sensor_state["ammonia_ppm"])) / 35.0
    cough = max(0.0, min(100.0, (ammonia_factor * 65.0) + random.uniform(3, 20)))
    stress = max(0.0, min(100.0, (float(behavior_state.get("edge_ratio", 0.0)) * 100.0) + random.uniform(2, 25)))
    respiratory = max(0.0, min(100.0, 100.0 - ((0.65 * cough) + (0.35 * stress))))

    acoustic_state.update(
        {
            "respiratory_health_index": round(respiratory, 2),
            "cough_index": round(cough, 2),
            "stress_audio_index": round(stress, 2),
            "source": "simulated_fallback",
            "updated_at": now,
        }
    )

    with app.app_context():
        row = AcousticReading(
            camera_id=ACTIVE_CAMERA_ID,
            respiratory_health_index=acoustic_state["respiratory_health_index"],
            cough_index=acoustic_state["cough_index"],
            stress_audio_index=acoustic_state["stress_audio_index"],
            source="simulated",
        )
        db.session.add(row)
        db.session.commit()
        _enqueue_sync_item("acoustic_reading", row.to_dict())

    if acoustic_state["cough_index"] > 70 or acoustic_state["respiratory_health_index"] < 45:
        _log_event(
            event_type="respiratory_alert",
            level="high",
            message="Indice respiratorio critico detectado pela analise acustica",
            metadata=acoustic_state,
        )
    last_acoustic_save_ts = now


def _update_energy_runtime():
    now = time.time()
    last_tick = float(energy_runtime_state.get("last_tick", now))
    delta = max(0.0, now - last_tick)
    energy_runtime_state["last_tick"] = now

    if estado_dispositivos.get("ventilacao"):
        energy_runtime_state["ventilacao_seconds_today"] += delta
    if estado_dispositivos.get("aquecedor"):
        energy_runtime_state["aquecedor_seconds_today"] += delta

    if delta <= 0:
        return
    day_start = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    with app.app_context():
        row = EnergyUsageDaily.query.filter_by(camera_id=ACTIVE_CAMERA_ID, day=day_start).first()
        if row is None:
            row = EnergyUsageDaily(camera_id=ACTIVE_CAMERA_ID, day=day_start)
            db.session.add(row)
        row.ventilacao_seconds = float(energy_runtime_state["ventilacao_seconds_today"])
        row.aquecedor_seconds = float(energy_runtime_state["aquecedor_seconds_today"])
        db.session.commit()


def _sync_worker():
    if requests is None:
        return
    while True:
        try:
            if CLOUD_SYNC_URL:
                with app.app_context():
                    pending = SyncQueueItem.query.filter_by(status="pending").order_by(SyncQueueItem.id.asc()).limit(50).all()
                    if pending:
                        payload = [p.to_dict() for p in pending]
                        try:
                            resp = requests.post(CLOUD_SYNC_URL, json={"items": payload}, timeout=12)
                            if resp.ok:
                                now = _utcnow()
                                for item in pending:
                                    item.status = "synced"
                                    item.synced_at = now
                                    item.attempts = int(item.attempts or 0) + 1
                                db.session.commit()
                            else:
                                for item in pending:
                                    item.attempts = int(item.attempts or 0) + 1
                                db.session.commit()
                        except Exception:
                            for item in pending:
                                item.attempts = int(item.attempts or 0) + 1
                            db.session.commit()
        except Exception as exc:
            LOGGER.exception("[SYNC] worker error: %s", exc)
        time.sleep(SYNC_PUSH_INTERVAL_SEC)


def _persist_sensor_reading(source="simulated"):
    with app.app_context():
        row = SensorReading(
            camera_id=ACTIVE_CAMERA_ID,
            temperature_c=float(sensor_state["temperature_c"]),
            humidity_pct=float(sensor_state["humidity_pct"]),
            ammonia_ppm=float(sensor_state["ammonia_ppm"]),
            feed_level_pct=float(sensor_state["feed_level_pct"]),
            water_level_pct=float(sensor_state["water_level_pct"]),
            source=source,
        )
        db.session.add(row)
        db.session.commit()
        _enqueue_sync_item("sensor_reading", row.to_dict())


def _maybe_alert_sensor(kind, value, message):
    now = time.time()
    last_ts = float(sensor_alert_state.get(kind, 0.0))
    if now - last_ts < SENSOR_ALERT_COOLDOWN_SEC:
        return
    sensor_alert_state[kind] = now
    _log_event(
        event_type="sensor_alert",
        level="high" if kind in ("ammonia", "water_low", "feed_low") else "medium",
        message=message,
        metadata={"kind": kind, "value": value},
    )


def _evaluate_sensor_alerts():
    h = float(sensor_state["humidity_pct"])
    a = float(sensor_state["ammonia_ppm"])
    f = float(sensor_state["feed_level_pct"])
    w = float(sensor_state["water_level_pct"])

    if h < sensor_thresholds["humidity_low"]:
        _maybe_alert_sensor("humidity_low", h, f"Umidade baixa: {h:.1f}%")
    if h > sensor_thresholds["humidity_high"]:
        _maybe_alert_sensor("humidity_high", h, f"Umidade alta: {h:.1f}%")
    if a > sensor_thresholds["ammonia_high"]:
        _maybe_alert_sensor("ammonia", a, f"Amonia elevada: {a:.1f} ppm")
    if f < sensor_thresholds["feed_low"]:
        _maybe_alert_sensor("feed_low", f, f"Racao baixa: {f:.1f}%")
    if w < sensor_thresholds["water_low"]:
        _maybe_alert_sensor("water_low", w, f"Agua baixa: {w:.1f}%")


def _simulate_sensor_updates(temp_atual):
    now = time.time()
    if now - float(sensor_state["updated_at"]) < SENSOR_SAVE_INTERVAL:
        return

    humidity = 68 - ((temp_atual - 24.0) * 1.3) + random.uniform(-2, 2)
    humidity = max(25.0, min(95.0, humidity))

    ammonia = float(sensor_state["ammonia_ppm"]) + random.uniform(-1.0, 1.1)
    ammonia = max(2.0, min(45.0, ammonia))

    feed = max(0.0, float(sensor_state["feed_level_pct"]) - random.uniform(0.1, 0.4))
    water = max(0.0, float(sensor_state["water_level_pct"]) - random.uniform(0.1, 0.5))

    sensor_state.update(
        {
            "temperature_c": round(float(temp_atual), 2),
            "humidity_pct": round(float(humidity), 2),
            "ammonia_ppm": round(float(ammonia), 2),
            "feed_level_pct": round(float(feed), 2),
            "water_level_pct": round(float(water), 2),
            "source": "simulated",
            "updated_at": now,
        }
    )

    _persist_sensor_reading(source="simulated")
    _evaluate_sensor_alerts()


def _apply_automatic_control(temp_atual):
    if not estado_dispositivos.get("modo_automatico"):
        return

    thresholds = _temperature_targets(ACTIVE_CAMERA_ID)
    changes = []

    if temp_atual >= thresholds["fan_on_temp"] and not estado_dispositivos["ventilacao"]:
        estado_dispositivos["ventilacao"] = True
        changes.append("ventilacao ligada")

    if temp_atual <= thresholds["fan_off_temp"] and estado_dispositivos["ventilacao"] and temp_atual < thresholds["fan_on_temp"]:
        estado_dispositivos["ventilacao"] = False
        changes.append("ventilacao desligada")

    if temp_atual <= thresholds["heater_on_temp"] and not estado_dispositivos["aquecedor"]:
        estado_dispositivos["aquecedor"] = True
        changes.append("aquecedor ligado")

    if temp_atual >= thresholds["heater_off_temp"] and estado_dispositivos["aquecedor"]:
        estado_dispositivos["aquecedor"] = False
        changes.append("aquecedor desligado")

    if changes:
        _log_event(
            event_type="automation_action",
            level="info",
            message=f"Acionamento automatico: {', '.join(changes)}",
            metadata={
                "temp_atual": round(float(temp_atual), 2),
                "thresholds": thresholds,
            },
        )

    # Weather-based pre-heating safety window (night cold front).
    hour = datetime.now().hour
    if weather_state.get("preheat_recommended") and (hour >= 18 or hour <= 6):
        if not estado_dispositivos["aquecedor"]:
            estado_dispositivos["aquecedor"] = True
            _log_event(
                event_type="weather_preheat",
                level="medium",
                message="Frente fria a chegar esta noite. O aquecedor foi pre-ativado.",
                metadata=weather_state,
            )


def _analyze_behavior(selected, frame_shape):
    now = time.time()
    count = len(selected)
    h, w = frame_shape[:2]
    frame_area = max(1, h * w)

    if count < 4:
        behavior_state.update(
            {
                "status": "NORMAL",
                "message": "Poucas aves no quadro para inferencia",
                "dispersion_ratio": 0.0,
                "edge_ratio": 0.0,
                "count": count,
                "updated_at": now,
            }
        )
        return

    centers = []
    for det in selected:
        cx, cy, _ = _box_center_area(det["box"])
        centers.append((cx, cy))

    xs = [c[0] for c in centers]
    ys = [c[1] for c in centers]
    spread_w = max(1, max(xs) - min(xs))
    spread_h = max(1, max(ys) - min(ys))
    spread_area = spread_w * spread_h
    dispersion_ratio = float(spread_area) / float(frame_area)

    margin = int(min(w, h) * 0.12)
    edge_count = 0
    for cx, cy in centers:
        if cx < margin or cx > (w - margin) or cy < margin or cy > (h - margin):
            edge_count += 1
    edge_ratio = float(edge_count) / float(max(1, count))

    status = "NORMAL"
    message = "Distribuicao comportamental normal"

    if dispersion_ratio < 0.12 and count >= 8:
        status = "FRIO_COMPORTAMENTAL"
        message = "Aviso: aves amontoadas. Possivel falha no aquecedor."
    elif edge_ratio > 0.45 and dispersion_ratio > 0.18 and count >= 8:
        status = "CALOR_COMPORTAMENTAL"
        message = "Aviso: aves nas bordas e dispersas. Possivel estresse termico por calor."

    behavior_state.update(
        {
            "status": status,
            "message": message,
            "dispersion_ratio": round(dispersion_ratio, 4),
            "edge_ratio": round(edge_ratio, 4),
            "count": count,
            "updated_at": now,
        }
    )

    if status != "NORMAL" and (now - float(behavior_state["last_alert_ts"])) >= BEHAVIOR_ALERT_COOLDOWN_SEC:
        behavior_state["last_alert_ts"] = now
        _log_event(
            event_type="behavior_alert",
            level="high" if status == "CALOR_COMPORTAMENTAL" else "medium",
            message=message,
            metadata={
                "status": status,
                "dispersion_ratio": behavior_state["dispersion_ratio"],
                "edge_ratio": behavior_state["edge_ratio"],
                "count": count,
            },
        )


def _update_immobility(selected):
    now = time.time()
    tracked_uids = set()

    for det in selected:
        uid = int(det.get("stable_bird_uid", -1))
        if uid < 0:
            continue
        tracked_uids.add(uid)
        cx, cy, _ = _box_center_area(det["box"])
        state = immobility_state.get(uid)
        if state is None:
            immobility_state[uid] = {
                "anchor": (cx, cy),
                "since": now,
                "last_seen": now,
                "alerted": False,
                "last_alert_ts": 0.0,
            }
            continue

        ax, ay = state["anchor"]
        dist = math.hypot(cx - ax, cy - ay)
        if dist <= IMMOBILITY_MOVE_PX:
            state["last_seen"] = now
        else:
            state["anchor"] = (cx, cy)
            state["since"] = now
            state["last_seen"] = now
            state["alerted"] = False

        stayed_sec = now - float(state["since"])
        since_last = now - float(state.get("last_alert_ts", 0.0))
        if stayed_sec >= IMMOBILITY_MIN_SEC and (not state["alerted"]) and since_last >= IMMOBILITY_ALERT_COOLDOWN_SEC:
            state["alerted"] = True
            state["last_alert_ts"] = now
            _log_event(
                event_type="immobility_alert",
                level="high",
                message=f"Possivel imobilidade detectada na ave UID {uid}",
                metadata={
                    "bird_uid": uid,
                    "x": cx,
                    "y": cy,
                    "immobile_seconds": round(stayed_sec, 1),
                },
            )

    stale_uids = []
    for uid, state in immobility_state.items():
        if uid in tracked_uids:
            continue
        if now - float(state.get("last_seen", now)) > (BIRD_LIVE_TTL_SEC + 5):
            stale_uids.append(uid)
    for uid in stale_uids:
        immobility_state.pop(uid, None)

def _telegram_send(frame_bgr, caption):
    token = SETTINGS.telegram_bot_token
    chat_id = SETTINGS.telegram_chat_id
    if not token or not chat_id:
        return False, "telegram_not_configured"
    if requests is None:
        return False, "requests_not_installed"

    ok, jpg = cv2.imencode(".jpg", frame_bgr)
    if not ok:
        return False, "jpeg_encode_failed"

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        response = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": ("intrusion.jpg", jpg.tobytes(), "image/jpeg")},
            timeout=10,
        )
        if response.ok:
            return True, "sent"
        return False, f"http_{response.status_code}"
    except Exception as exc:
        return False, str(exc)


def _telegram_send_text(message):
    token = SETTINGS.telegram_bot_token
    chat_id = SETTINGS.telegram_chat_id
    if not token or not chat_id or requests is None:
        return False, "telegram_not_configured"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=10)
        return (response.ok, f"http_{response.status_code}" if not response.ok else "sent")
    except Exception as exc:
        return False, str(exc)


def _trigger_local_alarm():
    try:
        for _ in range(3):
            if winsound is not None:
                winsound.Beep(1850, 280)
            else:
                print("\a", end="", flush=True)
            time.sleep(0.08)
    except Exception:
        pass


def _check_tampering(frame):
    global last_visible_frame, _tamper_prev_gray
    now = time.time()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_luma = float(np.mean(gray))
    std_luma = float(np.std(gray))
    visible_ok = mean_luma >= TAMPER_DARK_MEAN_THRESHOLD and std_luma >= TAMPER_LOW_TEXTURE_STD_THRESHOLD

    if visible_ok:
        tamper_state["dark_frames"] = 0
        last_visible_frame = frame.copy()
    else:
        tamper_state["dark_frames"] = int(tamper_state.get("dark_frames", 0)) + 1

    if _tamper_prev_gray is None:
        _tamper_prev_gray = gray
    else:
        diff = float(np.mean(cv2.absdiff(gray, _tamper_prev_gray)))
        if diff < TAMPER_FREEZE_DIFF_THRESHOLD:
            tamper_state["freeze_frames"] = int(tamper_state.get("freeze_frames", 0)) + 1
        else:
            tamper_state["freeze_frames"] = 0
        _tamper_prev_gray = gray

    sensor_stale = (now - float(sensor_state.get("updated_at", 0.0))) > float(TAMPER_SENSOR_STALE_SEC)
    tamper_state["sensor_stale"] = bool(sensor_stale)

    causes = []
    if int(tamper_state["dark_frames"]) >= 8:
        causes.append("camera_obstruida")
    if int(tamper_state["freeze_frames"]) >= TAMPER_FREEZE_MIN_FRAMES:
        causes.append("camera_congelada")
    if sensor_stale:
        causes.append("sensor_sem_update")
    if not causes:
        return

    if now - float(tamper_state.get("last_alert_ts", 0.0)) < TAMPER_ALERT_COOLDOWN_SEC:
        return

    tamper_state["last_alert_ts"] = now
    tamper_state["last_causes"] = list(causes)
    tamper_state["alerts_count"] = int(tamper_state.get("alerts_count", 0)) + 1
    _trigger_local_alarm()
    proof = last_visible_frame if last_visible_frame is not None else frame
    caption = (
        f"ALERTA CHIKGUARD: possivel sabotagem detectada "
        f"({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) - causas: {', '.join(causes)}"
    )
    sent, detail = _telegram_send(proof, caption)
    _log_event(
        event_type="tamper_alert",
        level="high",
        message="Possivel sabotagem detectada (anti-tampering)",
        metadata={
            "causes": causes,
            "telegram_sent": sent,
            "telegram_detail": detail,
            "dark_frames": int(tamper_state["dark_frames"]),
            "freeze_frames": int(tamper_state["freeze_frames"]),
            "sensor_stale": bool(sensor_stale),
        },
    )
    _audit(
        "tamper_alert_triggered",
        source="security",
        actor="chikguard-ai",
        details={"causes": causes, "telegram_sent": sent},
    )


def _update_carcass_detection(selected):
    now = time.time()
    carcasses = []
    for det in selected:
        uid = int(det.get("stable_bird_uid", -1))
        if uid < 0:
            continue
        x1, y1, x2, y2 = det["box"]
        box = (int(x1), int(y1), int(x2), int(y2))
        state = immobility_state.get(uid)
        if state is None:
            continue
        if "last_box" not in state:
            state["last_box"] = box
            state["same_box_since"] = now
            continue
        if tuple(state["last_box"]) == box:
            pass
        else:
            state["last_box"] = box
            state["same_box_since"] = now
            state["carcass_alerted"] = False
            continue
        still_seconds = now - float(state.get("same_box_since", now))
        if still_seconds >= CARCASS_STILL_SECONDS:
            cx, cy, _ = _box_center_area(det["box"])
            item = {
                "bird_uid": uid,
                "bbox": [box[0], box[1], box[2], box[3]],
                "x": cx,
                "y": cy,
                "sector": _sector_from_point(cx, cy, global_frame.shape if global_frame is not None else (720, 1280, 3)),
                "still_seconds": round(still_seconds, 1),
            }
            carcasses.append(item)
            if not state.get("carcass_alerted", False):
                state["carcass_alerted"] = True
                _log_event(
                    event_type="carcass_alert",
                    level="high",
                    message=f"Atencao: Possivel ave morta no setor {item['sector']}",
                    metadata=item,
                )
                _audit("carcass_alert_triggered", source="ai", actor="chikguard-ai", details=item)
    carcass_state["items"] = carcasses
    carcass_state["uids"] = set([c["bird_uid"] for c in carcasses])


def _fetch_weather_forecast_once():
    if not WEATHER_API_KEY or not WEATHER_LAT or not WEATHER_LON or requests is None:
        return
    try:
        url = (
            "https://api.openweathermap.org/data/2.5/forecast"
            f"?lat={WEATHER_LAT}&lon={WEATHER_LON}&appid={WEATHER_API_KEY}&units=metric&lang=pt_br"
        )
        resp = requests.get(url, timeout=12)
        if not resp.ok:
            return
        data = resp.json()
        entries = data.get("list", [])[:16]
        mins = []
        for e in entries:
            dt_txt = e.get("dt_txt", "")
            main = e.get("main", {})
            temp = main.get("temp_min", main.get("temp"))
            if temp is None:
                continue
            # Focus on upcoming night/madrugada windows.
            if "00:" in dt_txt or "03:" in dt_txt or "06:" in dt_txt:
                mins.append(float(temp))
        if not mins:
            mins = [float(e.get("main", {}).get("temp_min", 99)) for e in entries if e.get("main")]
        next_min = min(mins) if mins else None
        if next_min is None:
            return
        preheat = next_min <= WEATHER_COLD_FRONT_C
        weather_state.update(
            {
                "loaded": True,
                "next_night_min_c": round(float(next_min), 2),
                "preheat_recommended": bool(preheat),
                "message": (
                    f"Frente fria prevista: minima {next_min:.1f}C. Aquecedor sera pre-ativado."
                    if preheat
                    else f"Sem frente fria critica. Minima prevista: {next_min:.1f}C."
                ),
                "updated_at": time.time(),
            }
        )
        if preheat:
            _log_event("weather_cold_front", "medium", weather_state["message"], metadata=weather_state)
    except Exception as exc:
        LOGGER.exception("[WEATHER] fetch error: %s", exc)


def _weather_worker():
    while True:
        _fetch_weather_forecast_once()
        time.sleep(WEATHER_CHECK_INTERVAL_SEC)


def _comfort_score():
    temp_status_score = 100
    ultima = Reading.query.order_by(Reading.id.desc()).first()
    if ultima is not None:
        if ultima.status == "CALOR":
            temp_status_score = 65
        elif ultima.status == "FRIO":
            temp_status_score = 72
    intrusion_penalty = 25 if (time.time() - float(intrusion_state.get("last_alert_ts", 0.0))) < 3600 else 0
    movement_bonus = 8 if behavior_state.get("status") == "NORMAL" else -8
    carcass_penalty = min(30, len(carcass_state.get("items", [])) * 10)
    base = temp_status_score - intrusion_penalty - carcass_penalty + movement_bonus
    return int(max(0, min(100, base)))


def _detect_intrusion(all_detections, frame):
    now = time.time()
    hour = datetime.now().hour
    is_night_window = INTRUSION_START_HOUR <= hour <= INTRUSION_END_HOUR
    if not is_night_window:
        return

    person_dets = []
    for det in all_detections:
        cname = _class_name_by_id(det["class_id"]).lower()
        if cname == "person" and float(det["confidence"]) >= 0.35:
            person_dets.append(det)

    if not person_dets:
        return

    if now - float(intrusion_state["last_alert_ts"]) < INTRUSION_COOLDOWN_SEC:
        return

    intrusion_state["last_alert_ts"] = now
    caption = f"ALERTA CHIKGUARD: pessoa detectada de madrugada ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
    sent, detail = _telegram_send(frame, caption)
    _log_event(
        event_type="intrusion_alert",
        level="high",
        message="Intrusao detectada na camera",
        metadata={"detections": len(person_dets), "telegram": {"sent": sent, "detail": detail}},
    )
    _audit(
        "intrusion_alert_triggered",
        source="ai",
        actor="chikguard-ai",
        details={"detections": len(person_dets), "telegram_sent": sent},
    )


def _save_bird_snapshots(frame, ambient_temp):
    global last_bird_snapshot_save_time
    now = time.time()
    if now - last_bird_snapshot_save_time < BIRD_SNAPSHOT_SAVE_INTERVAL:
        return

    with lock:
        birds_items = list(live_birds.items())
    if not birds_items:
        last_bird_snapshot_save_time = now
        return

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rows = []
    for bird_uid, data in birds_items:
        box = data["box"]
        est_temp = _estimate_bird_temp_proxy(gray, box, ambient_temp)
        rows.append(
            BirdSnapshot(
                bird_uid=int(bird_uid),
                confidence=float(data["conf"]),
                x1=int(box[0]),
                y1=int(box[1]),
                x2=int(box[2]),
                y2=int(box[3]),
                temperatura_estimada=est_temp,
                metodo_temperatura="estimada_rgb_proxy",
            )
        )

    if rows:
        now_dt = _utcnow()
        with app.app_context():
            db.session.bulk_save_objects(rows)
            for row in rows:
                identity = BirdIdentity.query.filter_by(bird_uid=row.bird_uid).first()
                if identity is None:
                    identity = BirdIdentity(
                        bird_uid=row.bird_uid,
                        first_seen=now_dt,
                        last_seen=now_dt,
                        sightings=1,
                        max_confidence=row.confidence,
                        last_temp_estimada=row.temperatura_estimada,
                    )
                    db.session.add(identity)
                else:
                    identity.last_seen = now_dt
                    identity.sightings = int(identity.sightings) + 1
                    if row.confidence > float(identity.max_confidence):
                        identity.max_confidence = row.confidence
                    identity.last_temp_estimada = row.temperatura_estimada
            db.session.commit()
        _detect_thermal_anomalies(gray, ambient_temp, frame.shape)
        _persist_weight_estimate(frame.shape)

    last_bird_snapshot_save_time = now


def _save_bird_track_points():
    global last_track_point_save_time
    now = time.time()
    if now - last_track_point_save_time < TRACK_POINT_SAVE_INTERVAL:
        return

    with lock:
        birds_items = list(live_birds.items())
    if not birds_items:
        last_track_point_save_time = now
        return

    rows = []
    for bird_uid, data in birds_items:
        x1, y1, x2, y2 = data["box"]
        cx = int((int(x1) + int(x2)) / 2)
        cy = int((int(y1) + int(y2)) / 2)
        rows.append(BirdTrackPoint(bird_uid=int(bird_uid), x=cx, y=cy))

    with app.app_context():
        db.session.bulk_save_objects(rows)
        db.session.commit()
    last_track_point_save_time = now


def detectar_objetos(frame):
    global object_count
    draw_frame = frame.copy()
    detections = detector.detect(draw_frame)
    _detect_intrusion(detections, frame)

    frame_area = frame.shape[0] * frame.shape[1]
    min_bird_area = frame_area * MIN_BIRD_AREA_RATIO

    selected = []
    if MODO_DETECCAO == "aves":
        target_name = BIRD_CLASS_NAME.strip().lower()
        for det in detections:
            class_name = _class_name_by_id(det["class_id"]).lower()
            if class_name != target_name:
                continue
            x1, y1, x2, y2 = det["box"]
            area = max(0, x2 - x1) * max(0, y2 - y1)
            if area < min_bird_area:
                continue
            selected.append(det)
    else:
        selected = detections

    now = time.time()
    with lock:
        if MODO_DETECCAO == "aves":
            used_uids = set()
            for det in selected:
                tid = int(det["track_id"])
                if tid < 0:
                    continue
                stable_uid = _resolve_stable_bird_uid(tid, det["box"], now, frame, used_uids)
                used_uids.add(stable_uid)
                det["stable_bird_uid"] = stable_uid

                cx, cy, area = _box_center_area(det["box"])
                prev_state = bird_last_state.get(stable_uid)
                vx = 0.0
                vy = 0.0
                if prev_state is not None:
                    dt = max(1e-3, now - float(prev_state["last_seen"]))
                    px, py = prev_state["center"]
                    vx = (cx - float(px)) / dt
                    vy = (cy - float(py)) / dt

                bird_last_state[stable_uid] = {
                    "center": (cx, cy),
                    "area": area,
                    "last_seen": now,
                    "vx": vx,
                    "vy": vy,
                    "appearance": _extract_appearance_signature(frame, det["box"]),
                }

                live_birds[stable_uid] = {
                    "box": [int(v) for v in det["box"]],
                    "conf": float(det["confidence"]),
                    "last_seen": now,
                    "track_id": tid,
                    "mask_area_px": float(det.get("mask_area_px", 0.0)),
                }

            stale_live = [uid for uid, info in live_birds.items() if (now - float(info["last_seen"])) > BIRD_LIVE_TTL_SEC]
            for uid in stale_live:
                live_birds.pop(uid, None)

            stale_tracks = []
            for tracker_id, uid in track_to_bird_uid.items():
                last_state = bird_last_state.get(uid)
                if last_state is None or (now - float(last_state["last_seen"])) > (REID_MAX_GAP_SEC * 2):
                    stale_tracks.append(tracker_id)
            for tracker_id in stale_tracks:
                track_to_bird_uid.pop(tracker_id, None)

            stale_states = [uid for uid, state in bird_last_state.items() if (now - float(state["last_seen"])) > (REID_MAX_GAP_SEC * 4)]
            for uid in stale_states:
                bird_last_state.pop(uid, None)

            object_count = sum(1 for info in live_birds.values() if (now - float(info["last_seen"])) <= BIRD_LIVE_TTL_SEC)
        else:
            object_count = len(selected)

    if MODO_DETECCAO == "aves":
        _analyze_behavior(selected, frame.shape)
        _update_immobility(selected)
        _update_carcass_detection(selected)

    if detector.yolo_loaded:
        font = cv2.FONT_HERSHEY_PLAIN
        for det in selected:
            x1, y1, x2, y2 = det["box"]
            class_name = _class_name_by_id(det["class_id"]) or "obj"
            tid = int(det.get("stable_bird_uid", det["track_id"]))
            confidence = float(det["confidence"])
            is_carcass = tid in carcass_state.get("uids", set())
            color = (0, 0, 0) if is_carcass else (0, 255, 0)
            cv2.rectangle(draw_frame, (x1, y1), (x2, y2), color, 2)
            if is_carcass:
                label = f"POSSIVEL CARCACA ID:{tid}"
            else:
                label = f"{class_name} ID:{tid} ({confidence:.2f})" if tid >= 0 else f"{class_name} ({confidence:.2f})"
            cv2.putText(draw_frame, label, (x1, max(20, y1 - 5)), font, 1.2, color, 2)

    if MODO_DETECCAO == "aves":
        cv2.putText(draw_frame, f"Aves visiveis: {object_count}", (10, 30), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
        btxt = f"Comportamento: {behavior_state['status']}"
        cv2.putText(draw_frame, btxt, (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 220, 255), 1)
    else:
        cv2.putText(draw_frame, f"Objetos: {object_count}", (10, 30), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

    cfg = f"tracker={TRACKER_CONFIG} conf={DETECTION_CONF:.2f} classe={BIRD_CLASS_NAME}"
    cv2.putText(draw_frame, cfg, (10, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)
    return draw_frame


def _heatmap_grid(date_ref=None, grid_size=32):
    if date_ref is None:
        date_ref = _utcnow().date()

    start_dt = datetime.combine(date_ref, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)
    with app.app_context():
        rows = (
            BirdTrackPoint.query.filter(BirdTrackPoint.timestamp >= start_dt, BirdTrackPoint.timestamp < end_dt)
            .order_by(BirdTrackPoint.id.asc())
            .all()
        )
    if not rows:
        return np.zeros((grid_size, grid_size), dtype=np.float32)

    max_x = max(1, max(r.x for r in rows))
    max_y = max(1, max(r.y for r in rows))
    heat = np.zeros((grid_size, grid_size), dtype=np.float32)
    for row in rows:
        gx = min(grid_size - 1, int((row.x / max_x) * (grid_size - 1)))
        gy = min(grid_size - 1, int((row.y / max_y) * (grid_size - 1)))
        heat[gy, gx] += 1.0
    return heat


def _heatmap_grid_last_hours(hours=24, grid_size=32):
    end_dt = _utcnow()
    start_dt = end_dt - timedelta(hours=max(1, min(hours, 168)))
    with app.app_context():
        rows = (
            BirdTrackPoint.query.filter(BirdTrackPoint.timestamp >= start_dt, BirdTrackPoint.timestamp <= end_dt)
            .order_by(BirdTrackPoint.id.asc())
            .all()
        )
    if not rows:
        return np.zeros((grid_size, grid_size), dtype=np.float32)
    max_x = max(1, max(r.x for r in rows))
    max_y = max(1, max(r.y for r in rows))
    heat = np.zeros((grid_size, grid_size), dtype=np.float32)
    for row in rows:
        gx = min(grid_size - 1, int((row.x / max_x) * (grid_size - 1)))
        gy = min(grid_size - 1, int((row.y / max_y) * (grid_size - 1)))
        heat[gy, gx] += 1.0
    return heat


def _heatmap_image_bytes(heat):
    if np.max(heat) <= 0:
        canvas_img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(canvas_img, "Sem dados de movimentacao", (120, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
    else:
        norm = cv2.normalize(heat, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        resized = cv2.resize(norm, (640, 480), interpolation=cv2.INTER_CUBIC)
        canvas_img = cv2.applyColorMap(resized, cv2.COLORMAP_JET)
        cv2.putText(canvas_img, "Heatmap de movimentacao diario", (150, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    ok, buf = cv2.imencode(".jpg", canvas_img)
    if not ok:
        return None
    return buf.tobytes()


def _heatmap_points_3d(hours=24, grid_size=24):
    heat = _heatmap_grid_last_hours(hours=hours, grid_size=grid_size)
    if np.max(heat) <= 0:
        return []
    norm = cv2.normalize(heat, None, 0.0, 1.0, cv2.NORM_MINMAX)
    points = []
    h, w = norm.shape
    for gy in range(h):
        for gx in range(w):
            intensity = float(norm[gy, gx])
            if intensity < 0.05:
                continue
            ammonia_local = float(sensor_state.get("ammonia_ppm", 0.0)) * (0.7 + 0.6 * intensity)
            points.append(
                {
                    "x": round(gx / max(1, w - 1), 4),
                    "y": round(gy / max(1, h - 1), 4),
                    "z": round(intensity * 4.0, 4),
                    "heat_intensity": round(intensity, 4),
                    "ammonia_ppm": round(ammonia_local, 2),
                }
            )
    return points


def _simulate_airflow_field(fans=None, grid_size=24):
    fans = fans or [{"x": 0.5, "y": 0.2, "power": 1.0, "angle_deg": 90}]
    vectors = []
    for gy in range(grid_size):
        for gx in range(grid_size):
            x = gx / max(1, grid_size - 1)
            y = gy / max(1, grid_size - 1)
            vx = 0.0
            vy = 0.0
            for fan in fans:
                fx = float(fan.get("x", 0.5))
                fy = float(fan.get("y", 0.5))
                pw = max(0.0, float(fan.get("power", 1.0)))
                dx = x - fx
                dy = y - fy
                dist = math.sqrt((dx * dx) + (dy * dy)) + 1e-4
                influence = pw / (1.0 + (dist * 9.0))
                angle = math.atan2(dy, dx)
                vx += math.cos(angle) * influence
                vy += math.sin(angle) * influence
            mag = math.sqrt((vx * vx) + (vy * vy))
            vectors.append(
                {
                    "x": round(x, 4),
                    "y": round(y, 4),
                    "vx": round(vx, 4),
                    "vy": round(vy, 4),
                    "speed": round(mag, 4),
                }
            )
    avg_speed = sum(v["speed"] for v in vectors) / max(1, len(vectors))
    return {
        "grid_size": grid_size,
        "fans": fans,
        "avg_speed": round(avg_speed, 4),
        "vectors": vectors,
    }


def _energy_forecast(hours=12):
    hours = max(1, min(int(hours), 48))
    now = _utcnow()
    today_start = datetime(now.year, now.month, now.day)
    elapsed = max(60.0, (now - today_start).total_seconds())
    today_row = EnergyUsageDaily.query.filter_by(camera_id=ACTIVE_CAMERA_ID, day=today_start).first()
    fan_today = float(today_row.ventilacao_seconds) if today_row else 0.0
    heater_today = float(today_row.aquecedor_seconds) if today_row else 0.0

    fan_today = max(fan_today, float(energy_runtime_state.get("ventilacao_seconds_today", 0.0)))
    heater_today = max(heater_today, float(energy_runtime_state.get("aquecedor_seconds_today", 0.0)))
    fan_per_hour = fan_today / elapsed * 3600.0
    heater_per_hour = heater_today / elapsed * 3600.0

    cold_boost = 1.0
    next_min = weather_state.get("next_night_min_c")
    if next_min is not None:
        try:
            tmin = float(next_min)
            if tmin <= 0:
                cold_boost = 1.50
            elif tmin <= WEATHER_COLD_FRONT_C:
                cold_boost = 1.30
            elif tmin <= 8:
                cold_boost = 1.15
        except Exception:
            cold_boost = 1.0
    if bool(weather_state.get("preheat_recommended")):
        cold_boost = max(cold_boost, 1.25)

    projected_fan_sec = fan_per_hour * hours
    projected_heater_sec = heater_per_hour * hours * cold_boost
    fan_kwh = (projected_fan_sec / 3600.0) * VENTILACAO_POWER_KW
    heater_kwh = (projected_heater_sec / 3600.0) * AQUECEDOR_POWER_KW
    total_kwh = fan_kwh + heater_kwh
    heating_cost = heater_kwh * ENERGY_TARIFF_PER_KWH
    total_cost = total_kwh * ENERGY_TARIFF_PER_KWH
    estimated_saving = (heating_cost * 0.20) + ((fan_kwh * ENERGY_TARIFF_PER_KWH) * 0.08)

    message = (
        f"Previsao de gasto de R$ {heating_cost:.2f} em aquecimento nas proximas {hours}h. "
        f"Deseja otimizar o fluxo de ar?"
    )
    return {
        "hours": hours,
        "camera_id": ACTIVE_CAMERA_ID,
        "weather_factor": round(cold_boost, 3),
        "next_night_min_c": weather_state.get("next_night_min_c"),
        "projected_heater_cost": round(heating_cost, 2),
        "projected_total_cost": round(total_cost, 2),
        "projected_total_kwh": round(total_kwh, 3),
        "estimated_optimization_savings": round(estimated_saving, 2),
        "suggest_optimize_airflow": bool(heating_cost >= 40.0 or cold_boost > 1.15),
        "message": message,
    }


def _generate_weekly_report(camera_id, week_end=None):
    if canvas is None or A4 is None:
        raise RuntimeError("reportlab nao instalado. Instale reportlab no backend.")

    if week_end is None:
        week_end = _utcnow()
    week_start = week_end - timedelta(days=7)

    with app.app_context():
        readings = Reading.query.filter(Reading.timestamp >= week_start, Reading.timestamp <= week_end).all()
        sensors = SensorReading.query.filter(
            SensorReading.camera_id == camera_id,
            SensorReading.timestamp >= week_start,
            SensorReading.timestamp <= week_end,
        ).all()
        events = EventLog.query.filter(
            EventLog.camera_id == camera_id,
            EventLog.timestamp >= week_start,
            EventLog.timestamp <= week_end,
        ).all()

    temps = [r.temperatura for r in readings]
    temp_min = min(temps) if temps else None
    temp_max = max(temps) if temps else None
    temp_avg = (sum(temps) / len(temps)) if temps else None

    amms = [s.ammonia_ppm for s in sensors if s.ammonia_ppm is not None]
    hums = [s.humidity_pct for s in sensors if s.humidity_pct is not None]
    feed = [s.feed_level_pct for s in sensors if s.feed_level_pct is not None]
    water = [s.water_level_pct for s in sensors if s.water_level_pct is not None]

    fname = f"weekly_report_{camera_id}_{week_end.strftime('%Y%m%d_%H%M%S')}.pdf"
    path = os.path.join(REPORTS_DIR, fname)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 40

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, f"ChikGuard - Relatorio semanal ({camera_id})")
    y -= 26
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Periodo: {week_start.strftime('%Y-%m-%d')} ate {week_end.strftime('%Y-%m-%d')}")
    y -= 20

    lines = [
        f"Temperatura minima: {temp_min:.1f} C" if temp_min is not None else "Temperatura minima: sem dados",
        f"Temperatura maxima: {temp_max:.1f} C" if temp_max is not None else "Temperatura maxima: sem dados",
        f"Temperatura media: {temp_avg:.1f} C" if temp_avg is not None else "Temperatura media: sem dados",
        f"Alertas/eventos: {len(events)}",
        f"Umidade media: {sum(hums)/len(hums):.1f}%" if hums else "Umidade media: sem dados",
        f"Amonia media: {sum(amms)/len(amms):.1f} ppm" if amms else "Amonia media: sem dados",
        f"Racao media restante: {sum(feed)/len(feed):.1f}%" if feed else "Racao media restante: sem dados",
        f"Agua media restante: {sum(water)/len(water):.1f}%" if water else "Agua media restante: sem dados",
    ]
    for line in lines:
        c.drawString(40, y, line)
        y -= 16

    y -= 8
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Eventos recentes")
    y -= 18
    c.setFont("Helvetica", 9)
    for ev in sorted(events, key=lambda e: e.timestamp, reverse=True)[:20]:
        msg = f"{ev.timestamp.strftime('%Y-%m-%d %H:%M:%S')} [{ev.level}] {ev.event_type} - {ev.message}"
        c.drawString(40, y, msg[:110])
        y -= 13
        if y < 50:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 9)

    c.save()
    return path


def _generate_esg_report(camera_id, days=30):
    if canvas is None or A4 is None:
        raise RuntimeError("reportlab nao instalado. Instale reportlab no backend.")

    days = max(7, min(int(days), 120))
    end_dt = _utcnow()
    start_dt = end_dt - timedelta(days=days)

    with app.app_context():
        readings = Reading.query.filter(Reading.timestamp >= start_dt, Reading.timestamp <= end_dt).all()
        acoustic_rows = AcousticReading.query.filter(
            AcousticReading.camera_id == camera_id,
            AcousticReading.timestamp >= start_dt,
            AcousticReading.timestamp <= end_dt,
        ).all()
        events = EventLog.query.filter(
            EventLog.camera_id == camera_id,
            EventLog.timestamp >= start_dt,
            EventLog.timestamp <= end_dt,
        ).all()

    total = len(readings)
    normal = len([r for r in readings if r.status == "NORMAL"])
    calor = len([r for r in readings if r.status == "CALOR"])
    frio = len([r for r in readings if r.status == "FRIO"])
    low_stress_pct = (normal / total * 100.0) if total else 0.0
    thermal_stress_pct = (100.0 - low_stress_pct) if total else 0.0
    avg_resp = (
        sum(float(a.respiratory_health_index) for a in acoustic_rows) / len(acoustic_rows)
        if acoustic_rows
        else 100.0
    )
    critical_events = len([e for e in events if str(e.level).lower() == "high"])
    esg_score = max(0.0, min(100.0, (low_stress_pct * 0.55) + (avg_resp * 0.35) - (critical_events * 0.8)))
    market_flag = "APTO para mercados exigentes (Europa/Japao)" if esg_score >= 80 else "Necessita melhorias para mercados premium"

    fname = f"esg_report_{camera_id}_{end_dt.strftime('%Y%m%d_%H%M%S')}.pdf"
    path = os.path.join(REPORTS_DIR, fname)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, f"ChikGuard - Relatorio ESG ({camera_id})")
    y -= 24
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Periodo analisado: {start_dt.strftime('%Y-%m-%d')} ate {end_dt.strftime('%Y-%m-%d')}")
    y -= 22

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Indicadores de Sustentabilidade e Bem-Estar")
    y -= 18
    c.setFont("Helvetica", 10)
    lines = [
        f"Leituras termicas totais: {total}",
        f"Baixo stress termico (status NORMAL): {low_stress_pct:.1f}%",
        f"Stress termico (CALOR+FRIO): {thermal_stress_pct:.1f}%",
        f"Ocorrencias CALOR: {calor} | FRIO: {frio}",
        f"Saude respiratoria media (acustica): {avg_resp:.1f}/100",
        f"Eventos criticos de operacao: {critical_events}",
        f"ESG Score consolidado: {esg_score:.1f}/100",
        f"Status exportacao: {market_flag}",
    ]
    for line in lines:
        c.drawString(40, y, line)
        y -= 16

    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Conclusao automatica")
    y -= 16
    c.setFont("Helvetica", 10)
    conclusion = (
        "As aves apresentaram baixo stress termico e estabilidade ambiental, "
        "favorecendo conformidade ESG e valor agregado para exportacao."
        if esg_score >= 80
        else
        "Foram detectadas variacoes relevantes de conforto termico. Recomenda-se "
        "otimizar ventilacao, setpoint termico e rotina de monitoramento."
    )
    c.drawString(40, y, conclusion[:120])
    y -= 14
    if len(conclusion) > 120:
        c.drawString(40, y, conclusion[120:240])

    c.save()
    return path


def _send_report_email(file_path, recipient):
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    sender = os.getenv("SMTP_FROM", smtp_user).strip()

    if not smtp_host or not sender or not recipient:
        return False, "smtp_not_configured"

    msg = EmailMessage()
    msg["Subject"] = "ChikGuard - Relatorio semanal"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content("Segue o relatorio semanal do ChikGuard em anexo.")

    with open(file_path, "rb") as f:
        data = f.read()
    msg.add_attachment(data, maintype="application", subtype="pdf", filename=os.path.basename(file_path))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True, "sent"
    except Exception as exc:
        return False, str(exc)


def _weekly_report_scheduler():
    global last_weekly_report_key
    while True:
        try:
            now = datetime.now()
            key = f"{now.isocalendar().year}-W{now.isocalendar().week}"
            if now.weekday() == 6 and now.hour == 23 and key != last_weekly_report_key:
                path = _generate_weekly_report(ACTIVE_CAMERA_ID, week_end=now)
                last_weekly_report_key = key
                _log_event(
                    event_type="weekly_report",
                    level="info",
                    message="Relatorio semanal gerado automaticamente",
                    metadata={"file": path},
                )
        except Exception as exc:
            LOGGER.exception("[weekly-report] scheduler error: %s", exc)
        time.sleep(60)


def camera_loop():
    global global_frame, db_last_save_time, fps_last_time, last_temp_emergency_notification_ts
    cap = None
    use_basic_simulation = False
    video_sim = None
    last_error_print_time = 0.0
    consecutive_read_failures = 0
    last_reopen_attempt_ts = 0.0
    camera_lost_logged = False

    LOGGER.info("Starting video pipeline...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if cap.isOpened():
        use_basic_simulation = False
        _configure_camera_capture(cap)
    else:
        use_basic_simulation = True
        sim_msg = "Camera real nao encontrada. Simulacao basica ativada."
        sim_path = SIM_VIDEO_PATH
        if sim_path:
            sim_path = sim_path if os.path.isabs(sim_path) else os.path.join(os.path.dirname(__file__), sim_path)
            if VideoProcessor is not None and os.path.exists(sim_path):
                sim_msg = "Camera real nao encontrada. Simulacao em video ativada."
        _log_event("camera_fallback", "medium", sim_msg)

    while True:
        try:
            if use_basic_simulation:
                now_ts = time.time()
                if (now_ts - last_reopen_attempt_ts) >= CAMERA_REOPEN_INTERVAL_SEC:
                    last_reopen_attempt_ts = now_ts
                    try:
                        if cap is not None:
                            cap.release()
                    except Exception:
                        pass
                    cap = cv2.VideoCapture(CAMERA_INDEX)
                    if cap.isOpened():
                        _configure_camera_capture(cap)
                        use_basic_simulation = False
                        consecutive_read_failures = 0
                        camera_lost_logged = False
                        _log_event("camera_reconnected", "info", "Camera reconectada com sucesso.")
                        continue
                frame = None
                sim_path = SIM_VIDEO_PATH
                if sim_path:
                    sim_path = sim_path if os.path.isabs(sim_path) else os.path.join(os.path.dirname(__file__), sim_path)
                    if VideoProcessor is not None and os.path.exists(sim_path):
                        if video_sim is None:
                            try:
                                video_sim = VideoProcessor(sim_path)
                            except Exception:
                                video_sim = None
                        if video_sim is not None:
                            try:
                                frame = video_sim.get_next_frame()
                            except Exception:
                                video_sim = None
                if frame is None:
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.rectangle(frame, (200, 150), (350, 300), (0, 255, 0), 2)
                    cv2.putText(frame, "TEST_OBJECT", (200, 140), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
                    processed_frame = frame
                    temp_atual = 28 + random.uniform(-5, 5)
                else:
                    processed_frame = detectar_objetos(frame) if MODO_DETECCAO == "aves" else frame
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    temp_atual = 20 + (float(np.mean(gray)) / 255.0) * 20
            else:
                ret, frame = cap.read()
                if not ret:
                    consecutive_read_failures += 1
                    # Do not flap on transient read glitches.
                    if consecutive_read_failures < CAMERA_FAIL_THRESHOLD:
                        time.sleep(0.03)
                        continue
                    use_basic_simulation = True
                    consecutive_read_failures = 0
                    if not camera_lost_logged:
                        _log_event("camera_signal_lost", "high", "Perda de sinal prolongada. Simulacao ativada.")
                        camera_lost_logged = True
                    continue
                consecutive_read_failures = 0
                _check_tampering(frame)
                processed_frame = detectar_objetos(frame)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                temp_atual = 20 + (float(np.mean(gray)) / 255.0) * 20

            _apply_automatic_control(temp_atual)
            _simulate_sensor_updates(temp_atual)
            _simulate_acoustic_analysis()
            _update_energy_runtime()
            if temp_atual >= 35.0 and (time.time() - float(last_temp_emergency_notification_ts)) > 600:
                last_temp_emergency_notification_ts = time.time()
                txt = f"Temperatura subiu para {temp_atual:.1f}C! Intervencao necessaria."
                sent, detail = _telegram_send_text(txt)
                _log_event(
                    event_type="temperature_critical_alert",
                    level="high",
                    message=txt,
                    metadata={"telegram_sent": sent, "telegram_detail": detail},
                )

            new_time = time.time()
            fps = 1 / (new_time - fps_last_time) if (new_time - fps_last_time) > 0 else 0
            fps_last_time = new_time
            cv2.putText(
                processed_frame,
                f"FPS: {int(fps)}",
                (processed_frame.shape[1] - 120, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 0, 255),
                2,
            )

            with lock:
                global_frame = processed_frame

            if MODO_DETECCAO == "aves" and not use_basic_simulation:
                _save_bird_snapshots(frame, temp_atual)
                _save_bird_track_points()

            current_time = time.time()
            if current_time - db_last_save_time > 30:
                with app.app_context():
                    status = "NORMAL"
                    if temp_atual < 26:
                        status = "FRIO"
                    elif temp_atual > 32:
                        status = "CALOR"
                    reading = Reading(temperatura=round(temp_atual, 1), status=status)
                    db.session.add(reading)
                    db.session.commit()
                    _enqueue_sync_item("reading", reading.to_dict())

                    try:
                        socketio.emit("reading_update", {
                            "temperatura": round(temp_atual, 1),
                            "status": status,
                            "camera_id": ACTIVE_CAMERA_ID
                        })
                    except Exception as ws_exc:
                        LOGGER.warning("Failed to emit WebSocket reading: %s", ws_exc)

                db_last_save_time = current_time

        except Exception as exc:
            current_time = time.time()
            if current_time - last_error_print_time > 5:
                LOGGER.exception("CRITICAL ERROR IN CAMERA THREAD: %s", exc)
                last_error_print_time = current_time
            # Preserve the last good frame to avoid UI flicker on transient errors.
            with lock:
                if global_frame is None:
                    error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(error_frame, "THREAD ERROR", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
                    global_frame = error_frame
            time.sleep(1)


_init_bird_uid_counter()
t = threading.Thread(target=camera_loop, daemon=True)
t.start()
weekly_thread = threading.Thread(target=_weekly_report_scheduler, daemon=True)
weekly_thread.start()
sync_thread = threading.Thread(target=_sync_worker, daemon=True)
sync_thread.start()
weather_thread = threading.Thread(target=_weather_worker, daemon=True)
weather_thread.start()
hardware_thread = threading.Thread(target=_hardware_monitor_worker, daemon=True)
hardware_thread.start()

api_blueprint = create_api_blueprint(
    {
        "time": time,
        "cv2": cv2,
        "db": db,
        "bcrypt": bcrypt,
        "create_access_token": create_access_token,
        "request_ip": _request_ip,
        "audit": _audit,
        "utcnow": _utcnow,
        "login_attempt_state": login_attempt_state,
        "login_rate_window_sec": LOGIN_RATE_WINDOW_SEC,
        "login_rate_max_attempts": LOGIN_RATE_MAX_ATTEMPTS,
        "Account": Account,
        "User": User,
        "Reading": Reading,
        "lock": lock,
        "get_global_frame": lambda: global_frame,
        "get_object_count": lambda: object_count,
        "stream_jpeg_quality": STREAM_JPEG_QUALITY,
        "stream_frame_interval_sec": STREAM_FRAME_INTERVAL_SEC,
        "camera_thread": t,
        "weekly_thread": weekly_thread,
        "sync_thread": sync_thread,
        "weather_thread": weather_thread,
        "hardware_thread": hardware_thread,
        "settings": SETTINGS,
        "active_camera_id": ACTIVE_CAMERA_ID,
        "camera_index": CAMERA_INDEX,
    }
)
app.register_blueprint(api_blueprint)


@app.route("/api/birds/live", methods=["GET"])
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
            }
            for bid, data in live_birds.items()
            if (now - float(data["last_seen"])) <= BIRD_LIVE_TTL_SEC
        ]
    items.sort(key=lambda item: item["bird_uid"])
    return jsonify({"count": len(items), "ttl_seconds": BIRD_LIVE_TTL_SEC, "items": items})

@app.route("/api/birds/history", methods=["GET"])
def get_birds_history():
    limit = request.args.get("limit", default=300, type=int)
    limit = max(1, min(limit, 5000))
    rows = BirdSnapshot.query.order_by(BirdSnapshot.id.desc()).limit(limit).all()
    return jsonify([row.to_dict() for row in reversed(rows)])


@app.route("/api/birds/registry", methods=["GET"])
def get_birds_registry():
    limit = request.args.get("limit", default=500, type=int)
    limit = max(1, min(limit, 10000))
    rows = BirdIdentity.query.order_by(BirdIdentity.last_seen.desc()).limit(limit).all()
    return jsonify({"count": len(rows), "items": [row.to_dict() for row in rows]})


@app.route("/api/birds/path/<int:bird_uid>", methods=["GET"])
def get_bird_path(bird_uid):
    limit = request.args.get("limit", default=500, type=int)
    limit = max(1, min(limit, 5000))
    rows = (
        BirdTrackPoint.query.filter_by(bird_uid=bird_uid).order_by(BirdTrackPoint.id.desc()).limit(limit).all()
    )
    items = [row.to_dict() for row in reversed(rows)]
    return jsonify({"bird_uid": bird_uid, "count": len(items), "items": items})


@app.route("/api/behavior/live", methods=["GET"])
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


@app.route("/api/immobility/live", methods=["GET"])
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


@app.route("/api/carcass/live", methods=["GET"])
def carcass_live():
    items = carcass_state.get("items", [])
    return jsonify(
        {
            "count": len(items),
            "audio_alert": len(items) > 0,
            "message": "Atencao: Possivel ave morta no setor X" if items else "Sem carcacas detectadas",
            "items": items,
        }
    )


@app.route("/api/heatmap/daily", methods=["GET"])
def get_daily_heatmap():
    date_str = request.args.get("date")
    grid_size = request.args.get("grid", default=32, type=int)
    grid_size = max(8, min(grid_size, 128))
    try:
        date_ref = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else _utcnow().date()
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


@app.route("/api/heatmap/daily/image", methods=["GET"])
def get_daily_heatmap_image():
    date_str = request.args.get("date")
    try:
        date_ref = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else _utcnow().date()
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
    return send_file(BytesIO(img_bytes), mimetype="image/jpeg", as_attachment=False, download_name=file_name)


@app.route("/api/heatmap/rolling24", methods=["GET"])
def get_rolling24_heatmap():
    hours = request.args.get("hours", default=24, type=int)
    grid_size = request.args.get("grid", default=40, type=int)
    grid_size = max(8, min(grid_size, 128))
    heat = _heatmap_grid_last_hours(hours=hours, grid_size=grid_size)
    total = float(np.sum(heat))
    max_cell = float(np.max(heat))
    norm = (heat / max_cell).tolist() if max_cell > 0 else heat.tolist()
    return jsonify({"hours": hours, "grid_size": grid_size, "total_points": int(total), "matrix": norm})


@app.route("/api/heatmap/rolling24/image", methods=["GET"])
def get_rolling24_heatmap_image():
    hours = request.args.get("hours", default=24, type=int)
    heat = _heatmap_grid_last_hours(hours=hours, grid_size=40)
    img_bytes = _heatmap_image_bytes(heat)
    if img_bytes is None:
        return jsonify({"msg": "Falha ao gerar heatmap rolling"}), 500
    return send_file(BytesIO(img_bytes), mimetype="image/jpeg", as_attachment=False, download_name="heatmap_rolling24.jpg")


@app.route("/api/heatmap/3d", methods=["GET"])
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


@app.route("/api/airflow/simulate", methods=["POST"])
def airflow_simulate():
    payload = request.get_json(silent=True) or {}
    fans = payload.get("fans")
    grid_size = int(payload.get("grid_size", 24))
    grid_size = max(8, min(grid_size, 40))
    if fans is not None and not isinstance(fans, list):
        return jsonify({"msg": "Campo fans deve ser lista"}), 400
    result = _simulate_airflow_field(fans=fans, grid_size=grid_size)
    return jsonify(result)


@app.route("/api/sensors/live", methods=["GET"])
def get_sensors_live():
    return jsonify(
        {
            "camera_id": ACTIVE_CAMERA_ID,
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


@app.route("/api/security/tamper", methods=["GET"])
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


@app.route("/api/sensors/history", methods=["GET"])
def get_sensors_history():
    limit = request.args.get("limit", default=100, type=int)
    limit = max(1, min(limit, 5000))
    rows = (
        SensorReading.query.filter_by(camera_id=ACTIVE_CAMERA_ID)
        .order_by(SensorReading.id.desc())
        .limit(limit)
        .all()
    )
    return jsonify({"count": len(rows), "items": [r.to_dict() for r in reversed(rows)]})


@app.route("/api/sensors/ingest", methods=["POST"])
def ingest_sensor_data():
    payload = request.get_json(silent=True) or {}
    required = ["temperature_c", "humidity_pct", "ammonia_ppm", "feed_level_pct", "water_level_pct"]
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
    _persist_sensor_reading(source=sensor_state["source"])
    _evaluate_sensor_alerts()
    return jsonify({"msg": "Leitura de sensores recebida", "state": sensor_state}), 200


@app.route("/api/weight/live", methods=["GET"])
def weight_live():
    return jsonify(
        {
            "camera_id": ACTIVE_CAMERA_ID,
            "avg_weight_g": weight_state["avg_weight_g"],
            "ideal_weight_g": weight_state["ideal_weight_g"],
            "count": weight_state["count"],
            "confidence": weight_state["confidence"],
            "updated_at_epoch": weight_state["updated_at"],
        }
    )


@app.route("/api/weight/curve", methods=["GET"])
def weight_curve():
    days = request.args.get("days", default=21, type=int)
    days = max(1, min(days, 120))
    start_dt = _utcnow() - timedelta(days=days)
    rows = (
        WeightEstimate.query.filter(WeightEstimate.camera_id == ACTIVE_CAMERA_ID, WeightEstimate.timestamp >= start_dt)
        .order_by(WeightEstimate.timestamp.asc())
        .all()
    )
    points = [r.to_dict() for r in rows]
    return jsonify({"count": len(points), "items": points})


@app.route("/api/acoustic/live", methods=["GET"])
def acoustic_live():
    return jsonify(
        {
            "camera_id": ACTIVE_CAMERA_ID,
            "respiratory_health_index": acoustic_state["respiratory_health_index"],
            "cough_index": acoustic_state["cough_index"],
            "stress_audio_index": acoustic_state["stress_audio_index"],
            "source": acoustic_state["source"],
            "updated_at_epoch": acoustic_state["updated_at"],
        }
    )


@app.route("/api/acoustic/model-info", methods=["GET"])
def acoustic_model_info():
    return jsonify(
        {
            "loaded": bool(audio_classifier.loaded),
            "model_path": audio_classifier.model_path,
            "last_error": audio_classifier.last_error,
            "librosa_available": librosa is not None,
            "soundfile_available": sf is not None,
        }
    )


@app.route("/api/acoustic/classify", methods=["POST"])
def acoustic_classify():
    if not audio_classifier.loaded:
        return jsonify({"msg": "Modelo de tosse nao carregado", "model_error": audio_classifier.last_error}), 400
    if sf is None:
        return jsonify({"msg": "Dependencia soundfile nao disponivel no backend"}), 500
    f = request.files.get("audio")
    if f is None:
        return jsonify({"msg": "Envie arquivo de audio no campo 'audio'"}), 400
    try:
        raw = f.read()
        y, sr = sf.read(io.BytesIO(raw), always_2d=False)
        if isinstance(y, np.ndarray) and y.ndim > 1:
            y = np.mean(y, axis=1)
        result = audio_classifier.classify(y, int(sr))
        if result is None:
            return jsonify({"msg": "Falha na inferencia de tosse", "error": audio_classifier.last_error}), 500

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
            camera_id=ACTIVE_CAMERA_ID,
            respiratory_health_index=acoustic_state["respiratory_health_index"],
            cough_index=acoustic_state["cough_index"],
            stress_audio_index=acoustic_state["stress_audio_index"],
            source="trained_model",
        )
        with app.app_context():
            db.session.add(row)
            db.session.commit()
            _enqueue_sync_item("acoustic_reading", row.to_dict())
        if acoustic_state["cough_index"] > 60:
            _log_event(
                event_type="respiratory_alert",
                level="high",
                message="Pico de tosse detectado por modelo acustico treinado",
                metadata={"cough_index": acoustic_state["cough_index"], "source": "trained_model"},
            )
        _audit(
            "acoustic_file_classified",
            source="manual",
            details={"source": "trained_model", "cough_index": acoustic_state["cough_index"]},
        )
        return jsonify({"msg": "Audio classificado com sucesso", "result": acoustic_state})
    except Exception as exc:
        return jsonify({"msg": f"Falha ao processar audio: {exc}"}), 500


@app.route("/api/acoustic/history", methods=["GET"])
def acoustic_history():
    limit = request.args.get("limit", default=200, type=int)
    limit = max(1, min(limit, 5000))
    rows = (
        AcousticReading.query.filter_by(camera_id=ACTIVE_CAMERA_ID)
        .order_by(AcousticReading.id.desc())
        .limit(limit)
        .all()
    )
    return jsonify({"count": len(rows), "items": [r.to_dict() for r in reversed(rows)]})


@app.route("/api/acoustic/ingest", methods=["POST"])
def acoustic_ingest():
    payload = request.get_json(silent=True) or {}
    required = ["respiratory_health_index", "cough_index", "stress_audio_index"]
    missing = [k for k in required if k not in payload]
    if missing:
        return jsonify({"msg": f"Campos obrigatorios ausentes: {', '.join(missing)}"}), 400
    acoustic_state.update(
        {
            "respiratory_health_index": float(payload["respiratory_health_index"]),
            "cough_index": float(payload["cough_index"]),
            "stress_audio_index": float(payload["stress_audio_index"]),
            "source": str(payload.get("source", "external")),
            "updated_at": time.time(),
        }
    )
    row = AcousticReading(
        camera_id=ACTIVE_CAMERA_ID,
        respiratory_health_index=acoustic_state["respiratory_health_index"],
        cough_index=acoustic_state["cough_index"],
        stress_audio_index=acoustic_state["stress_audio_index"],
        source=acoustic_state["source"],
    )
    with app.app_context():
        db.session.add(row)
        db.session.commit()
        _enqueue_sync_item("acoustic_reading", row.to_dict())
    return jsonify({"msg": "Leitura acustica recebida", "state": acoustic_state}), 200


@app.route("/api/thermal-anomalies/live", methods=["GET"])
def thermal_anomalies_live():
    last_minutes = request.args.get("minutes", default=20, type=int)
    start = _utcnow() - timedelta(minutes=max(1, min(last_minutes, 240)))
    rows = (
        ThermalAnomaly.query.filter(ThermalAnomaly.camera_id == ACTIVE_CAMERA_ID, ThermalAnomaly.timestamp >= start)
        .order_by(ThermalAnomaly.id.desc())
        .limit(200)
        .all()
    )
    items = [r.to_dict() for r in rows]
    sectors = sorted(list({i["sector"] for i in items if i.get("sector")}))
    return jsonify({"count": len(items), "sectors": sectors, "items": items})


@app.route("/api/energy/summary", methods=["GET"])
def energy_summary():
    now = _utcnow()
    month_start = datetime(now.year, now.month, 1)
    rows = (
        EnergyUsageDaily.query.filter(EnergyUsageDaily.camera_id == ACTIVE_CAMERA_ID, EnergyUsageDaily.day >= month_start)
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


@app.route("/api/energy/forecast", methods=["GET"])
def energy_forecast():
    hours = request.args.get("hours", default=12, type=int)
    with app.app_context():
        forecast = _energy_forecast(hours=hours)
    return jsonify(forecast)


@app.route("/api/audit/logs", methods=["GET"])
def audit_logs():
    limit = request.args.get("limit", default=200, type=int)
    limit = max(1, min(limit, 5000))
    rows = AuditLog.query.order_by(AuditLog.id.desc()).limit(limit).all()
    return jsonify({"count": len(rows), "items": [r.to_dict() for r in rows]})


@app.route("/api/sync/status", methods=["GET"])
def sync_status():
    pending = SyncQueueItem.query.filter_by(status="pending").count()
    synced = SyncQueueItem.query.filter_by(status="synced").count()
    failed = SyncQueueItem.query.filter_by(status="failed").count()
    return jsonify(
        {
            "pending": pending,
            "synced": synced,
            "failed": failed,
            "cloud_sync_url_configured": bool(CLOUD_SYNC_URL),
        }
    )


@app.route("/api/sync/pending", methods=["GET"])
def sync_pending():
    limit = request.args.get("limit", default=200, type=int)
    limit = max(1, min(limit, 2000))
    rows = SyncQueueItem.query.filter_by(status="pending").order_by(SyncQueueItem.id.asc()).limit(limit).all()
    return jsonify({"count": len(rows), "items": [r.to_dict() for r in rows]})


@app.route("/api/sync/ack", methods=["POST"])
def sync_ack():
    payload = request.get_json(silent=True) or {}
    ids = payload.get("ids", [])
    if not isinstance(ids, list) or not ids:
        return jsonify({"msg": "Forneca lista de ids"}), 400
    rows = SyncQueueItem.query.filter(SyncQueueItem.id.in_(ids)).all()
    now = _utcnow()
    for row in rows:
        row.status = "synced"
        row.synced_at = now
    db.session.commit()
    return jsonify({"msg": "Itens marcados como sincronizados", "count": len(rows)})


@app.route("/api/accounts/me", methods=["GET"])
def accounts_me():
    ok, resp = _guard_critical_action("accounts_me_view", permission="monitor.read")
    if not ok:
        return resp
    account = _get_current_account()
    if account is None:
        return jsonify({"msg": "Conta nao encontrada"}), 404
    return jsonify(account.to_dict())


@app.route("/api/accounts/users", methods=["GET", "POST"])
def accounts_users():
    ok, resp = _guard_critical_action("accounts_manage", permission="accounts.manage")
    if not ok:
        return resp
    if request.method == "GET":
        rows = Account.query.order_by(Account.id.asc()).all()
        return jsonify({"count": len(rows), "items": [r.to_dict() for r in rows]})

    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    role = str(data.get("role", "operator")).strip().lower()
    active = bool(data.get("active", True))
    if not username or not password:
        return jsonify({"msg": "username e password sao obrigatorios"}), 400
    if role not in ("admin", "operator", "viewer"):
        return jsonify({"msg": "role invalido"}), 400
    if Account.query.filter_by(username=username).first() is not None:
        return jsonify({"msg": "usuario ja existe"}), 409
    row = Account(
        username=username,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        role=role,
        active=active,
    )
    db.session.add(row)
    db.session.commit()
    _audit("account_created", source="security", details={"username": username, "role": role, "active": active})
    return jsonify({"msg": "Conta criada", "item": row.to_dict()}), 201


@app.route("/api/accounts/users/<int:account_id>", methods=["PATCH"])
def accounts_user_update(account_id):
    ok, resp = _guard_critical_action("accounts_manage", permission="accounts.manage")
    if not ok:
        return resp
    row = Account.query.get(account_id)
    if row is None:
        return jsonify({"msg": "Conta nao encontrada"}), 404
    data = request.get_json(silent=True) or {}
    if "role" in data:
        role = str(data.get("role", "")).strip().lower()
        if role not in ("admin", "operator", "viewer"):
            return jsonify({"msg": "role invalido"}), 400
        row.role = role
    if "active" in data:
        row.active = bool(data.get("active"))
    if "password" in data:
        pwd = str(data.get("password", "")).strip()
        if len(pwd) < 6:
            return jsonify({"msg": "password muito curto (min 6)"}), 400
        row.password_hash = bcrypt.generate_password_hash(pwd).decode("utf-8")
    db.session.commit()
    _audit("account_updated", source="security", details={"account_id": account_id, "payload_keys": list(data.keys())})
    return jsonify({"msg": "Conta atualizada", "item": row.to_dict()})


@app.route("/api/accounts/permissions", methods=["GET", "POST"])
def accounts_permissions():
    ok, resp = _guard_critical_action("permissions_manage", permission="accounts.manage")
    if not ok:
        return resp
    if request.method == "GET":
        rows = RolePermission.query.order_by(RolePermission.role.asc(), RolePermission.permission.asc()).all()
        return jsonify({"count": len(rows), "items": [r.to_dict() for r in rows]})

    data = request.get_json(silent=True) or {}
    role = str(data.get("role", "")).strip().lower()
    permission = str(data.get("permission", "")).strip()
    allowed = bool(data.get("allowed", True))
    if role not in ("admin", "operator", "viewer") or not permission:
        return jsonify({"msg": "role e permission sao obrigatorios"}), 400
    row = RolePermission.query.filter_by(role=role, permission=permission).first()
    if row is None:
        row = RolePermission(role=role, permission=permission, allowed=allowed)
        db.session.add(row)
    else:
        row.allowed = allowed
    db.session.commit()
    _audit("permission_updated", source="security", details={"role": role, "permission": permission, "allowed": allowed})
    return jsonify({"msg": "Permissao atualizada", "item": row.to_dict()})


@app.route("/api/auto-mode", methods=["GET", "POST"])
def auto_mode():
    if request.method == "GET":
        targets = _temperature_targets(ACTIVE_CAMERA_ID)
        return jsonify(
            {
                "enabled": bool(estado_dispositivos["modo_automatico"]),
                "config": auto_config,
                "effective_targets": targets,
                "camera_id": ACTIVE_CAMERA_ID,
            }
        )
    ok, resp = _guard_critical_action("auto_mode_change", permission="automation.manage")
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

    _log_event(
        event_type="auto_mode_config",
        level="info",
        message=f"Modo automatico {'ativado' if estado_dispositivos['modo_automatico'] else 'desativado'}",
        metadata={"config": auto_config},
    )
    _audit(
        "auto_mode_changed",
        source="manual",
        details={"enabled": estado_dispositivos["modo_automatico"], "config": auto_config},
    )
    return jsonify({"enabled": estado_dispositivos["modo_automatico"], "config": auto_config})


@app.route("/api/ventilacao", methods=["POST"])
def controlar_ventilacao():
    data = request.get_json(silent=True) or {}
    if "ligar" not in data:
        return jsonify({"msg": "Parametro 'ligar' e obrigatorio"}), 400
    ligar = bool(data["ligar"])
    perm = "device.power_on" if ligar else "device.power_off"
    ok, resp = _guard_critical_action("ventilacao_toggle", permission=perm)
    if not ok:
        return resp
    estado_dispositivos["ventilacao"] = ligar
    _log_event(
        event_type="manual_device_action",
        level="info",
        message=f"Ventilacao {'ligada' if estado_dispositivos['ventilacao'] else 'desligada'} manualmente",
    )
    _audit(
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


@app.route("/api/aquecedor", methods=["POST"])
def controlar_aquecedor():
    data = request.get_json(silent=True) or {}
    if "ligar" not in data:
        return jsonify({"msg": "Parametro 'ligar' e obrigatorio"}), 400
    ligar = bool(data["ligar"])
    perm = "device.power_on" if ligar else "device.power_off"
    ok, resp = _guard_critical_action("aquecedor_toggle", permission=perm)
    if not ok:
        return resp
    estado_dispositivos["aquecedor"] = ligar
    _log_event(
        event_type="manual_device_action",
        level="info",
        message=f"Aquecedor {'ligado' if estado_dispositivos['aquecedor'] else 'desligado'} manualmente",
    )
    _audit(
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


@app.route("/api/luz-dimmer", methods=["GET", "POST"])
def controlar_luz_dimmer():
    if request.method == "GET":
        return jsonify({"luz_intensidade_pct": int(estado_dispositivos.get("luz_intensidade_pct", 0))})
    ok, resp = _guard_critical_action("light_dimmer_change", permission="lighting.manage")
    if not ok:
        return resp
    data = request.get_json(silent=True) or {}
    intensidade = int(data.get("intensidade_pct", 0))
    intensidade = max(0, min(100, intensidade))
    estado_dispositivos["luz_intensidade_pct"] = intensidade
    _log_event("light_dimmer_changed", "info", f"Intensidade da luz ajustada para {intensidade}%")
    _audit("light_dimmer_changed", source="manual", details={"intensidade_pct": intensidade})
    return jsonify({"luz_intensidade_pct": intensidade, "msg": "Dimmer atualizado"})


@app.route("/api/voice/command", methods=["POST"])
def voice_command():
    data = request.get_json(silent=True) or {}
    command = str(data.get("text", "")).strip().lower()
    if not command:
        return jsonify({"msg": "Comando vazio"}), 400
    action = None
    if "ligar ventil" in command:
        estado_dispositivos["ventilacao"] = True
        action = "ventilacao_on"
    elif "desligar ventil" in command:
        estado_dispositivos["ventilacao"] = False
        action = "ventilacao_off"
    elif "ligar aquec" in command:
        estado_dispositivos["aquecedor"] = True
        action = "aquecedor_on"
    elif "desligar aquec" in command:
        estado_dispositivos["aquecedor"] = False
        action = "aquecedor_off"
    elif "luz" in command and "%" in command:
        try:
            pct = int("".join([c for c in command if c.isdigit()]))
            pct = max(0, min(100, pct))
            estado_dispositivos["luz_intensidade_pct"] = pct
            action = "luz_dimmer"
        except Exception:
            pass
    if action is None:
        return jsonify({"msg": "Comando nao reconhecido", "text": command}), 400
    action_perm = "voice.command"
    if action in ("ventilacao_off", "aquecedor_off"):
        action_perm = "device.power_off"
    elif action in ("ventilacao_on", "aquecedor_on"):
        action_perm = "device.power_on"
    elif action == "luz_dimmer":
        action_perm = "lighting.manage"
    ok, resp = _guard_critical_action("voice_command_control", permission=action_perm)
    if not ok:
        return resp
    _audit("voice_command_executed", source="mobile_voice", details={"command": command, "action": action})
    return jsonify({"msg": "Comando executado", "action": action, "devices": estado_dispositivos})


@app.route("/api/estado-dispositivos", methods=["GET"])
def get_estado_dispositivos():
    return jsonify(estado_dispositivos)


@app.route("/api/hardware-health", methods=["GET"])
def get_hardware_health():
    return jsonify(hardware_state)


@app.route("/api/events", methods=["GET"])
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


@app.route("/api/cameras", methods=["GET", "POST"])
def cameras():
    if request.method == "GET":
        return jsonify({"active_camera_id": ACTIVE_CAMERA_ID, "items": camera_registry})

    data = request.get_json(silent=True) or {}
    camera_id = str(data.get("camera_id", "")).strip()
    source = str(data.get("source", "")).strip()
    if not camera_id or not source:
        return jsonify({"msg": "camera_id e source sao obrigatorios"}), 400
    if any(c["camera_id"] == camera_id for c in camera_registry):
        return jsonify({"msg": "camera_id ja cadastrado"}), 400
    camera_registry.append({"camera_id": camera_id, "source": source, "enabled": bool(data.get("enabled", True))})
    _log_event("camera_registry", "info", f"Camera cadastrada: {camera_id}", {"source": source})
    return jsonify({"msg": "Camera cadastrada", "items": camera_registry}), 201


@app.route("/api/batches", methods=["GET", "POST"])
def batches():
    if request.method == "GET":
        rows = Batch.query.filter_by(camera_id=ACTIVE_CAMERA_ID).order_by(Batch.id.desc()).all()
        return jsonify({"count": len(rows), "items": [r.to_dict() for r in rows]})

    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    start_date_raw = str(data.get("start_date", "")).strip()
    notes = str(data.get("notes", "")).strip() or None
    if not name or not start_date_raw:
        return jsonify({"msg": "name e start_date (YYYY-MM-DD) sao obrigatorios"}), 400
    try:
        start_date = datetime.strptime(start_date_raw, "%Y-%m-%d")
    except Exception:
        return jsonify({"msg": "start_date invalido. Use YYYY-MM-DD"}), 400

    with app.app_context():
        if bool(data.get("active", True)):
            Batch.query.filter_by(camera_id=ACTIVE_CAMERA_ID, active=True).update({"active": False})
        row = Batch(
            camera_id=ACTIVE_CAMERA_ID,
            name=name,
            start_date=start_date,
            active=bool(data.get("active", True)),
            notes=notes,
        )
        db.session.add(row)
        db.session.commit()
    _log_event("batch_created", "info", f"Lote criado: {name}", {"start_date": start_date_raw})
    return jsonify({"msg": "Lote criado", "item": row.to_dict()}), 201


@app.route("/api/batches/<int:batch_id>/activate", methods=["POST"])
def activate_batch(batch_id):
    with app.app_context():
        row = Batch.query.get(batch_id)
        if row is None:
            return jsonify({"msg": "Lote nao encontrado"}), 404
        Batch.query.filter_by(camera_id=row.camera_id, active=True).update({"active": False})
        row.active = True
        db.session.commit()
    _log_event("batch_activated", "info", f"Lote ativado: {row.name}", {"batch_id": batch_id})
    return jsonify({"msg": "Lote ativado", "item": row.to_dict()})


@app.route("/api/logbook", methods=["GET", "POST"])
def logbook():
    if request.method == "GET":
        limit = request.args.get("limit", default=100, type=int)
        limit = max(1, min(limit, 1000))
        rows = BatchLogbook.query.filter_by(camera_id=ACTIVE_CAMERA_ID).order_by(BatchLogbook.id.desc()).limit(limit).all()
        return jsonify({"count": len(rows), "items": [r.to_dict() for r in rows]})
    data = request.get_json(silent=True) or {}
    note = str(data.get("note", "")).strip()
    author = str(data.get("author", "")).strip() or "operador"
    if not note:
        return jsonify({"msg": "Campo note e obrigatorio"}), 400
    batch = _active_batch(ACTIVE_CAMERA_ID)
    row = BatchLogbook(
        camera_id=ACTIVE_CAMERA_ID,
        batch_id=batch.id if batch else None,
        note=note,
        author=author,
    )
    with app.app_context():
        db.session.add(row)
        db.session.commit()
        _enqueue_sync_item("logbook", row.to_dict())
    _audit("logbook_note_created", source="manual", actor=author, details={"batch_id": row.batch_id})
    return jsonify({"msg": "Nota registrada", "item": row.to_dict()}), 201


@app.route("/api/weather/forecast", methods=["GET"])
def weather_forecast():
    return jsonify(weather_state)


@app.route("/api/reports/esg", methods=["POST"])
def generate_esg_report():
    data = request.get_json(silent=True) or {}
    days = int(data.get("days", 30))
    email = str(data.get("email", "")).strip() or None
    try:
        path = _generate_esg_report(ACTIVE_CAMERA_ID, days=days)
    except Exception as exc:
        return jsonify({"msg": f"Falha ao gerar PDF ESG: {exc}"}), 500

    email_status = None
    if email:
        ok, detail = _send_report_email(path, email)
        email_status = {"sent": ok, "detail": detail, "email": email}

    _log_event(
        event_type="esg_report",
        level="info",
        message="Relatorio ESG gerado",
        metadata={"file": path, "days": days, "email_status": email_status},
    )
    return jsonify({"msg": "Relatorio ESG gerado", "file": path, "email_status": email_status})


@app.route("/api/reports/esg/download", methods=["GET"])
def download_esg_report():
    days = request.args.get("days", default=30, type=int)
    try:
        path = _generate_esg_report(ACTIVE_CAMERA_ID, days=days)
        return send_file(path, mimetype="application/pdf", as_attachment=True, download_name=os.path.basename(path))
    except Exception as exc:
        return jsonify({"msg": f"Falha ao gerar/exportar PDF ESG: {exc}"}), 500


@app.route("/api/reports/weekly", methods=["POST"])
def generate_weekly_report():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip() or None
    try:
        path = _generate_weekly_report(ACTIVE_CAMERA_ID)
    except Exception as exc:
        return jsonify({"msg": f"Falha ao gerar PDF: {exc}"}), 500

    email_status = None
    if email:
        ok, detail = _send_report_email(path, email)
        email_status = {"sent": ok, "detail": detail, "email": email}

    _log_event(
        event_type="weekly_report",
        level="info",
        message="Relatorio semanal gerado manualmente",
        metadata={"file": path, "email_status": email_status},
    )
    return jsonify({"msg": "Relatorio gerado", "file": path, "email_status": email_status})


@app.route("/api/reports/weekly/download", methods=["GET"])
def download_weekly_report():
    try:
        path = _generate_weekly_report(ACTIVE_CAMERA_ID)
        _log_event(
            event_type="weekly_report",
            level="info",
            message="Relatorio semanal exportado pelo painel",
            metadata={"file": path},
        )
        return send_file(path, mimetype="application/pdf", as_attachment=True, download_name=os.path.basename(path))
    except Exception as exc:
        return jsonify({"msg": f"Falha ao gerar/exportar PDF: {exc}"}), 500


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    itens = []

    recentes = Reading.query.order_by(Reading.id.desc()).limit(50).all()
    for item in recentes:
        if item.status == "NORMAL":
            continue
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
            }
        )

    event_rows = (
        EventLog.query.filter_by(camera_id=ACTIVE_CAMERA_ID).order_by(EventLog.id.desc()).limit(50).all()
    )
    for ev in event_rows:
        itens.append(
            {
                "id": f"event-{ev.id}",
                "tipo": ev.event_type.upper(),
                "nivel": "alto" if ev.level == "high" else "medio" if ev.level == "medium" else "baixo",
                "mensagem": ev.message,
                "temperatura": None,
                "hora": ev.timestamp.strftime("%H:%M:%S"),
                "data": ev.timestamp.strftime("%d/%m/%Y"),
            }
        )

    itens.sort(key=lambda x: f"{x['data']} {x['hora']}", reverse=True)
    return jsonify(itens[:100])


@app.route("/api/summary", methods=["GET"])
def get_summary():
    ok, resp = _guard_critical_action("summary_view", permission="monitor.read")
    if not ok:
        return resp
    ultima = Reading.query.order_by(Reading.id.desc()).first()
    recentes = Reading.query.order_by(Reading.id.desc()).limit(30).all()
    temperaturas = [item.temperatura for item in recentes]
    alertas = [item for item in recentes if item.status != "NORMAL"]
    total_vistas = BirdIdentity.query.count()

    now = time.time()
    with lock:
        count = object_count
        alive_count = sum(1 for info in live_birds.values() if (now - float(info["last_seen"])) <= BIRD_LIVE_TTL_SEC)

    targets = _temperature_targets(ACTIVE_CAMERA_ID)
    batch = _active_batch(ACTIVE_CAMERA_ID)
    pending_sync = SyncQueueItem.query.filter_by(status="pending").count()
    today = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    energy_today = EnergyUsageDaily.query.filter_by(camera_id=ACTIVE_CAMERA_ID, day=today).first()
    vent_sec_today = float(energy_today.ventilacao_seconds) if energy_today else 0.0
    aq_sec_today = float(energy_today.aquecedor_seconds) if energy_today else 0.0
    return jsonify(
        {
            "temperatura_atual": ultima.temperatura if ultima else 0,
            "status_atual": ultima.status if ultima else "INICIANDO",
            "media_temperatura": round(sum(temperaturas) / len(temperaturas), 1) if temperaturas else 0,
            "contagem_aves": count,
            "aves_vivas_individuais": alive_count,
            "total_aves_vistas": total_vistas,
            "metodo_temperatura_ave": "estimada_rgb_proxy",
            "tracker": TRACKER_CONFIG,
            "classe_ave": BIRD_CLASS_NAME,
            "dispositivos": estado_dispositivos,
            "total_alertas": len(alertas),
            "modo_deteccao": MODO_DETECCAO,
            "camera_id": ACTIVE_CAMERA_ID,
            "behavior": {
                "status": behavior_state["status"],
                "message": behavior_state["message"],
                "dispersion_ratio": behavior_state["dispersion_ratio"],
                "edge_ratio": behavior_state["edge_ratio"],
            },
            "sensors": {
                "humidity_pct": sensor_state["humidity_pct"],
                "ammonia_ppm": sensor_state["ammonia_ppm"],
                "feed_level_pct": sensor_state["feed_level_pct"],
                "water_level_pct": sensor_state["water_level_pct"],
            },
            "automation": {
                "enabled": bool(estado_dispositivos["modo_automatico"]),
                "targets": targets,
            },
            "batch": batch.to_dict() if batch else None,
            "weight": {
                "avg_weight_g": weight_state["avg_weight_g"],
                "ideal_weight_g": weight_state["ideal_weight_g"],
                "confidence": weight_state["confidence"],
                "method": "segmentation_area" if detector.supports_segmentation else "bbox_area_fallback",
            },
            "acoustic": {
                "respiratory_health_index": acoustic_state["respiratory_health_index"],
                "cough_index": acoustic_state["cough_index"],
                "stress_audio_index": acoustic_state["stress_audio_index"],
                "source": acoustic_state["source"],
                "trained_model_loaded": bool(audio_classifier.loaded),
            },
            "energy_today": {
                "ventilacao_seconds": round(vent_sec_today, 2),
                "aquecedor_seconds": round(aq_sec_today, 2),
            },
            "smart_grid_forecast_12h": _energy_forecast(hours=12),
            "sync": {"pending": pending_sync},
            "weather": weather_state,
            "tamper": {
                "last_alert_ts": float(tamper_state.get("last_alert_ts", 0.0)),
                "last_causes": tamper_state.get("last_causes", []),
                "alerts_count": int(tamper_state.get("alerts_count", 0)),
            },
            "carcass": {
                "count": len(carcass_state.get("items", [])),
                "audio_alert": len(carcass_state.get("items", [])) > 0,
            },
            "comfort_score": _comfort_score(),
        }
    )


@app.route("/api/system-info", methods=["GET"])
def get_system_info():
    uptime_seconds = int(time.time() - APP_START_TIME)
    return jsonify(
        {
            "uptime_seconds": uptime_seconds,
            "camera_thread_alive": t.is_alive(),
            "weekly_scheduler_alive": weekly_thread.is_alive(),
            "sync_thread_alive": sync_thread.is_alive(),
            "weather_thread_alive": weather_thread.is_alive(),
            "hardware_thread_alive": hardware_thread.is_alive(),
            "modo_deteccao": MODO_DETECCAO,
            "yolo_loaded": detector.yolo_loaded,
            "yolo_segmentation": bool(detector.supports_segmentation),
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
            "cough_model_loaded": bool(audio_classifier.loaded),
            "cough_model_path": COUGH_MODEL_PATH,
        }
    )


@app.route("/api/plugins", methods=["GET"])
def get_plugins():
    items = PLUGIN_MANAGER.list_plugins()
    return jsonify({"count": len(items), "plugins": items, "plugins_root": PLUGINS_ROOT})


@app.route("/api/plugins/reload", methods=["POST"])
def reload_plugins():
    ok, resp = _guard_critical_action("plugins_reload")
    if not ok:
        return resp
    PLUGIN_MANAGER.load_all({"logger": LOGGER, "settings": SETTINGS})
    items = PLUGIN_MANAGER.list_plugins()
    _audit("plugins_reloaded", source="backend", details={"count": len(items)})
    return jsonify({"msg": "Plugins recarregados", "count": len(items), "plugins": items})


if __name__ == "__main__":
    LOGGER.info(
        "Starting API (with WebSockets) host=%s port=%s env=%s",
        SETTINGS.flask_host,
        SETTINGS.flask_port,
        SETTINGS.app_env,
    )
    socketio.run(app, host=SETTINGS.flask_host, port=SETTINGS.flask_port, debug=False, allow_unsafe_werkzeug=True)

