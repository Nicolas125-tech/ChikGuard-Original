import time
import os
import json
from sqlalchemy.orm import Session
from src.core.state import active_camera_id, sensor_state, sensor_thresholds
from src.core.logger import configure_logging

# Since we are running with PYTHONPATH=., we can import from database directly
from database import SensorReading, EventLog, SyncQueueItem

logger = configure_logging()
SENSOR_ALERT_COOLDOWN_SEC = int(os.getenv("SENSOR_ALERT_COOLDOWN_SEC", "300"))
sensor_alert_state = {}

def _safe_json(obj):
    try:
        return json.dumps(obj)
    except Exception:
        return "{}"

def persist_sensor_reading(db: Session, source: str = "sensor"):
    try:
        row = SensorReading(
            camera_id=active_camera_id,
            temperature_c=float(sensor_state.get("temperature_c", 0.0)),
            humidity_pct=float(sensor_state.get("humidity_pct", 0.0)),
            ammonia_ppm=float(sensor_state.get("ammonia_ppm", 0.0)),
            feed_level_pct=float(sensor_state.get("feed_level_pct", 0.0)),
            water_level_pct=float(sensor_state.get("water_level_pct", 0.0)),
            source=source,
        )
        db.add(row)
        db.flush()  # Obtém o ID autogerado sem encerrar a transação

        # Enqueue sync item
        sync_item = SyncQueueItem(
            item_type="sensor_reading",
            payload_json=_safe_json(row.to_dict()),
            status="pending"
        )
        db.add(sync_item)
        db.commit()  # Confirma ambas as inserções de forma atômica
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to persist sensor reading: {e}")

def _maybe_alert_sensor(db: Session, kind: str, value: float, message: str):
    now = time.time()
    last_ts = float(sensor_alert_state.get(kind, 0.0))
    if now - last_ts < SENSOR_ALERT_COOLDOWN_SEC:
        return
    sensor_alert_state[kind] = now

    level = "high" if kind in ("ammonia", "water_low", "feed_low") else "medium"
    try:
        event = EventLog(
            camera_id=active_camera_id,
            event_type="sensor_alert",
            level=level,
            message=message,
            metadata_json=_safe_json({"kind": kind, "value": value})
        )
        db.add(event)
        db.flush()  # Obtém o ID autogerado sem encerrar a transação

        sync_item = SyncQueueItem(
            item_type="event_log",
            payload_json=_safe_json(event.to_dict()),
            status="pending"
        )
        db.add(sync_item)
        db.commit()  # Confirma ambas as inserções de forma atômica
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create sensor alert event log: {e}")

def evaluate_sensor_alerts(db: Session):
    h = float(sensor_state.get("humidity_pct", 0.0))
    a = float(sensor_state.get("ammonia_ppm", 0.0))
    f = float(sensor_state.get("feed_level_pct", 0.0))
    w = float(sensor_state.get("water_level_pct", 0.0))

    hum_low = sensor_thresholds.get("humidity_low", 40.0)
    hum_high = sensor_thresholds.get("humidity_high", 75.0)
    amm_high = sensor_thresholds.get("ammonia_high", 20.0)
    f_low = sensor_thresholds.get("feed_low", 20.0)
    w_low = sensor_thresholds.get("water_low", 20.0)

    if h < hum_low:
        _maybe_alert_sensor(db, "humidity_low", h, f"Umidade baixa: {h:.1f}%")
    if h > hum_high:
        _maybe_alert_sensor(db, "humidity_high", h, f"Umidade alta: {h:.1f}%")
    if a > amm_high:
        _maybe_alert_sensor(db, "ammonia", a, f"Amonia elevada: {a:.1f} ppm")
    if f < f_low:
        _maybe_alert_sensor(db, "feed_low", f, f"Racao baixa: {f:.1f}%")
    if w < w_low:
        _maybe_alert_sensor(db, "water_low", w, f"Agua baixa: {w:.1f}%")
