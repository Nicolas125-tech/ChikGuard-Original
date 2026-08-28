"""
fastapi_zone_analytics.py - Endpoints REST de Séries Temporais e Frequência por Zona (Saltoratto et al., 2013)
Expõe métricas de permanência no Bebedouro, Aquecimento e Comedouro.

Persistência Poliglota:
  - MongoDB (cv_track_points, cv_detections) → dados brutos de trajetória e detecção
  - state.zone_time_series_tracker → acumulador in-memory (real-time)
  - Fallback: dados do tracker in-memory se MongoDB estiver vazio
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query

from src.core import state
from src.infrastructure.db.nosql_session import get_nosql_db
from src.security.fastapi_auth import UserContext, get_current_user

logger = logging.getLogger("chikguard.api.zone_analytics")

router = APIRouter(prefix="/api/analytics", tags=["zone-analytics"])


# ---------------------------------------------------------------------------
# MongoDB-backed zone analytics
# ---------------------------------------------------------------------------

async def _get_zone_series_from_mongo(
    camera_id: str, limit: int, hours: int
) -> list | None:
    """
    Queries cv_track_points in MongoDB, groups by time buckets, and computes
    zone occupancy time series.

    Zones are derived from x/y coordinates using predefined regions:
      - Bebedouro (Drinker):  left 1/3 of frame
      - Aquecedor (Brooder):  center 1/3 of frame
      - Comedouro (Feeder):   right 1/3 of frame
    """
    try:
        db = get_nosql_db()
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        pipeline = [
            {
                "$match": {
                    "camera_id": camera_id,
                    "timestamp": {"$gte": cutoff},
                }
            },
            {
                "$addFields": {
                    "zone": {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {"$lt": ["$x", 213]},
                                    "then": "drinker",
                                },
                                {
                                    "case": {"$lt": ["$x", 426]},
                                    "then": "brooder",
                                },
                            ],
                            "default": "feeder",
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "zone": "$zone",
                        # Bucket timestamps into 1-minute intervals
                        "minute": {
                            "$substr": ["$timestamp", 0, 16]
                        },
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.minute": 1}},
            {"$limit": limit},
        ]

        cursor = db["cv_track_points"].aggregate(pipeline)
        results = await cursor.to_list(length=limit)

        if not results:
            return None

        series = []
        for r in results:
            series.append({
                "zone": r["_id"]["zone"],
                "timestamp": r["_id"]["minute"],
                "count": r["count"],
            })

        return series

    except Exception as exc:
        logger.warning(f"MongoDB zone series query failed: {exc}")
        return None


async def _get_zone_summary_from_mongo(camera_id: str) -> dict | None:
    """
    Returns cumulative zone frequency summary from MongoDB cv_track_points.
    """
    try:
        db = get_nosql_db()

        pipeline = [
            {"$match": {"camera_id": camera_id}},
            {
                "$addFields": {
                    "zone": {
                        "$switch": {
                            "branches": [
                                {"case": {"$lt": ["$x", 213]}, "then": "drinker"},
                                {"case": {"$lt": ["$x", 426]}, "then": "brooder"},
                            ],
                            "default": "feeder",
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": "$zone",
                    "total": {"$sum": 1},
                }
            },
        ]

        cursor = db["cv_track_points"].aggregate(pipeline)
        results = await cursor.to_list(length=10)

        if not results:
            return None

        zone_map = {r["_id"]: r["total"] for r in results}
        total = sum(zone_map.values())

        most_freq = max(zone_map, key=zone_map.get) if zone_map else "NENHUMA"
        zone_labels = {"drinker": "BEBEDOURO", "brooder": "AQUECEDOR", "feeder": "COMEDOURO"}

        return {
            "total_samples": total,
            "cumulative_drinker": zone_map.get("drinker", 0),
            "cumulative_brooder": zone_map.get("brooder", 0),
            "cumulative_feeder": zone_map.get("feeder", 0),
            "most_frequented_zone": zone_labels.get(most_freq, most_freq.upper()),
            "source": "mongodb",
        }

    except Exception as exc:
        logger.warning(f"MongoDB zone summary query failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/zone-time-series")
async def get_zone_time_series(
    limit: int = Query(default=100, ge=1, le=1000),
    hours: int = Query(default=24, ge=1, le=168),
    camera_id: str = Query(default="galpao-1"),
    user: UserContext = Depends(get_current_user),
):
    """
    Retorna a série temporal de permanência por zona (Figura 20 e 21 do artigo).
    Busca primeiramente no MongoDB (cv_track_points), com fallback para o tracker in-memory.
    """
    # Priority 1: MongoDB
    mongo_series = await _get_zone_series_from_mongo(camera_id, limit, hours)
    if mongo_series:
        return {
            "count": len(mongo_series),
            "items": mongo_series,
            "source": "mongodb",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    # Priority 2: In-memory tracker (original behavior)
    tracker = getattr(state, "zone_time_series_tracker", None)
    if tracker is None:
        return {"count": 0, "items": [], "source": "none"}

    series = tracker.get_time_series(limit=limit)
    return {
        "count": len(series),
        "items": series,
        "source": "in_memory",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/zone-summary")
async def get_zone_summary(
    camera_id: str = Query(default="galpao-1"),
    user: UserContext = Depends(get_current_user),
):
    """
    Retorna o somatório acumulado de frequências de permanência por zona (Figura 22 do artigo).
    Busca primeiramente no MongoDB, com fallback para o tracker in-memory.
    """
    # Priority 1: MongoDB
    mongo_summary = await _get_zone_summary_from_mongo(camera_id)
    if mongo_summary:
        mongo_summary["generated_at"] = datetime.utcnow().isoformat() + "Z"
        return mongo_summary

    # Priority 2: In-memory tracker (original behavior)
    tracker = getattr(state, "zone_time_series_tracker", None)
    if tracker is None:
        return {
            "total_samples": 0,
            "cumulative_drinker": 0,
            "cumulative_brooder": 0,
            "cumulative_feeder": 0,
            "most_frequented_zone": "NENHUMA",
            "source": "none",
        }

    summary = tracker.get_cumulative_summary()
    summary["generated_at"] = datetime.utcnow().isoformat() + "Z"
    summary["source"] = "in_memory"
    return summary
