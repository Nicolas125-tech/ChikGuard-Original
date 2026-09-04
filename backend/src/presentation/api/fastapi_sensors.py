import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.db.session import get_async_db
from src.core.sensors_utils import persist_sensor_reading, evaluate_sensor_alerts
from src.core.state import active_camera_id, sensor_state, sensor_thresholds
from src.domain.schemas.sensors import SensorIngest, SensorLiveResponse
from src.security.fastapi_auth import get_current_user, UserContext, RequireRole

router = APIRouter(prefix="/api/sensors", tags=["sensors"])

@router.get("/live", response_model=SensorLiveResponse)
async def get_sensors_live(user: UserContext = Depends(get_current_user)):
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
async def ingest_sensor_data(
    payload: SensorIngest,
    db: AsyncSession = Depends(get_async_db),
    user: UserContext = Depends(RequireRole(["operator", "admin", "superadmin"])),
):
    """Recebe novos dados de sensores via Edge/IoT e atualiza o estado."""
    sensor_state.update(
        {
            "temperature_c": payload.temperature_c,
            "humidity_pct": payload.humidity_pct,
            "ammonia_ppm": payload.ammonia_ppm,
            "feed_level_pct": payload.feed_level_pct,
            "water_level_pct": payload.water_level_pct,
            "source": payload.source,
            "updated_at": time.time(),
        }
    )

    # Convertendo as utilidades para chamadas thread-pool (para não bloquear o event loop se forem síncronas internamente)
    import asyncio
    loop = asyncio.get_event_loop()
    raw_session = getattr(db, "sync_session", db)
    await loop.run_in_executor(None, lambda: persist_sensor_reading(raw_session, source=payload.source))
    await loop.run_in_executor(None, lambda: evaluate_sensor_alerts(raw_session))

    return {"msg": "Leitura de sensores recebida", "state": sensor_state}
