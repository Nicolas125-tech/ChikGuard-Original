import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.core.state import active_camera_id, sensor_state, sensor_thresholds
from src.schemas.sensors import SensorIngest, SensorLiveResponse
from src.security.fastapi_auth import get_current_user, UserContext

router = APIRouter(prefix="/api/sensors", tags=["sensors"])

@router.get("/live", response_model=SensorLiveResponse)
def get_sensors_live(user: UserContext = Depends(get_current_user)):
    """Retorna o estado atual dos sensores."""
    return {
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

@router.post("/ingest")
def ingest_sensor_data(
    payload: SensorIngest, 
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user)
):
    """Recebe novos dados de sensores via Edge/IoT e atualiza o estado."""
    sensor_state.update({
        "temperature_c": payload.temperature_c,
        "humidity_pct": payload.humidity_pct,
        "ammonia_ppm": payload.ammonia_ppm,
        "feed_level_pct": payload.feed_level_pct,
        "water_level_pct": payload.water_level_pct,
        "source": payload.source,
        "updated_at": time.time(),
    })
    
    # TODO: Integrar persist_sensor_reading(db) e evaluate_sensor_alerts()
    
    return {"msg": "Leitura de sensores recebida", "state": sensor_state}
