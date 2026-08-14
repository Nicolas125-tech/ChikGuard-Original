import time
import numpy as np

# Estados globais migrados do app.py
active_camera_id = "galpao-1"

sensor_state = {
    "temperature_c": 0.0,
    "humidity_pct": 0.0,
    "ammonia_ppm": 0.0,
    "feed_level_pct": 0.0,
    "water_level_pct": 0.0,
    "source": "init",
    "updated_at": time.time(),
}

sensor_thresholds = {
    "temp_min": 18.0,
    "temp_max": 32.0,
    "ammonia_max": 20.0,
    "humidity_min": 40.0,
    "humidity_max": 75.0,
}

acoustic_state = {
    "respiratory_health_index": 100.0,
    "cough_index": 0.0,
    "stress_audio_index": 0.0,
    "source": "init",
    "updated_at": time.time(),
}

import threading

# Lock para states compartilhados entre Threads de CV e async FastAPI
cv_lock = threading.Lock()

# CV States
live_birds = {}
species_counts = {"chicks": 0, "hens": 0, "total": 0}

weight_state = {
    "avg_weight_g": 0.0,
    "ideal_weight_g": 0.0,
    "count": 0,
    "confidence": 0.0,
    "updated_at": time.time(),
}

behavior_state = {
    "status": "NORMAL",
    "message": "Comportamento dentro dos parâmetros padrão",
    "dispersion_ratio": 0.5,
    "edge_ratio": 0.1,
    "count": 0,
    "updated_at": time.time(),
}

immobility_state = {}

carcass_state = {
    "count": 0,
    "items": [],
    "updated_at": time.time(),
}

tamper_state = {
    "last_alert_ts": 0.0,
    "last_causes": [],
    "alerts_count": 0,
    "dark_frames": 0,
    "freeze_frames": 0,
}

TAMPER_SENSOR_STALE_SEC = 60.0

intrusion_state = {
    "active": False,
    "last_alert_ts": 0.0,
    "alerts_count": 0
}

zone_analytics_state = {
    "drinker_count": 0,
    "brooder_count": 0,
    "feeder_count": 0,
    "drinker_pct": 0.0,
    "brooder_pct": 0.0,
    "feeder_pct": 0.0,
    "welfare_status": "CONFORTO_IDEAL",
    "welfare_message": "Ambiência Adequada: Distribuição homogênea entre comedouro, bebedouro e aquecimento",
    "welfare_index": 0.95,
    "updated_at": time.time(),
}

spatial_accumulator = None
zone_time_series_tracker = None

global_frame_data = np.zeros((480, 640, 3), dtype=np.uint8)

def get_global_frame():
    global global_frame_data
    return global_frame_data

def set_global_frame(frame):
    global global_frame_data
    global_frame_data = frame


_default_get_global_frame = get_global_frame


