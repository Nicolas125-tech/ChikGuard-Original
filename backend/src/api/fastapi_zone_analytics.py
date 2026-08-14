"""
fastapi_zone_analytics.py - Endpoints REST de Séries Temporais e Frequência por Zona (Saltoratto et al., 2013)
Expõe métricas de permanência no Bebedouro, Aquecimento e Comedouro.
"""

from fastapi import APIRouter, Depends, Query
from src.security.fastapi_auth import get_current_user, UserContext
from datetime import datetime
from src.core import state

router = APIRouter(prefix="/api/analytics", tags=["zone-analytics"])


@router.get("/zone-time-series")
async def get_zone_time_series(
    limit: int = Query(default=100, ge=1, le=1000),
    user: UserContext = Depends(get_current_user),
):
    """
    Retorna a série temporal de permanência por zona (Figura 20 e 21 do artigo).
    """
    tracker = getattr(state, "zone_time_series_tracker", None)
    if tracker is None:
        return {"count": 0, "items": []}

    series = tracker.get_time_series(limit=limit)
    return {
        "count": len(series),
        "items": series,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/zone-summary")
async def get_zone_summary(
    user: UserContext = Depends(get_current_user),
):
    """
    Retorna o somatório acumulado de frequências de permanência por zona (Figura 22 do artigo).
    """
    tracker = getattr(state, "zone_time_series_tracker", None)
    if tracker is None:
        return {
            "total_samples": 0,
            "cumulative_drinker": 0,
            "cumulative_brooder": 0,
            "cumulative_feeder": 0,
            "most_frequented_zone": "NENHUMA",
        }

    summary = tracker.get_cumulative_summary()
    summary["generated_at"] = datetime.utcnow().isoformat() + "Z"
    return summary
