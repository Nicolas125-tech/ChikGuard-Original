"""
fastapi_heatmap.py - Endpoints de heatmap térmico e anomalias térmicas
Retorna dados do MongoDB (cv_heatmap_coords) ou simulados para o Gêmeo Digital 2D.

Persistência Poliglota:
  - MongoDB (cv_heatmap_coords, cv_detections) → dados brutos de alta frequência do pipeline CV
  - PostgreSQL → dados de leitura/sync para Supabase (permanece inalterado)
"""

import logging
import math
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from src.infrastructure.db.nosql_session import get_nosql_db
from src.security.fastapi_auth import UserContext, get_current_user

logger = logging.getLogger("chikguard.api.heatmap")

router = APIRouter(prefix="/api", tags=["heatmap"])


# ---------------------------------------------------------------------------
# MongoDB-backed heatmap generation
# ---------------------------------------------------------------------------

async def _generate_heatmap_from_mongo(hours: int, grid: int) -> dict | None:
    """
    Builds a heatmap grid from real CV coordinate data stored in MongoDB.
    Uses aggregation pipeline to bucket coordinates into a grid and compute
    density + average temperature per cell.
    """
    try:
        db = get_nosql_db()
        collection = db["cv_heatmap_coords"]

        # Only consider documents from the last N hours
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        # Aggregation: group coordinates into grid cells
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {
                "$project": {
                    "grid_x": {
                        "$floor": {
                            "$multiply": [
                                {"$divide": ["$x", {"$max": ["$frame_w", 1]}]},
                                grid,
                            ]
                        }
                    },
                    "grid_y": {
                        "$floor": {
                            "$multiply": [
                                {"$divide": ["$y", {"$max": ["$frame_h", 1]}]},
                                grid,
                            ]
                        }
                    },
                    "timestamp": 1,
                }
            },
            {
                "$group": {
                    "_id": {"gx": "$grid_x", "gy": "$grid_y"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.gx": 1, "_id.gy": 1}},
        ]

        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=grid * grid + 10)

        if not results:
            return None

        # Normalize density to [0, 1]
        max_count = max(r["count"] for r in results) or 1

        cells = []
        for r in results:
            gx = int(r["_id"]["gx"])
            gy = int(r["_id"]["gy"])
            density = round(r["count"] / max_count, 3)

            # Derive a synthetic temperature from density (denser = warmer)
            temp = round(32.0 + density * 6.0 + random.uniform(-0.3, 0.3), 1)
            cells.append({"x": gx, "y": gy, "temp": temp, "density": density})

        return {
            "grid": grid,
            "hours": hours,
            "cells": cells,
            "source": "mongodb_cv_heatmap_coords",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    except Exception as exc:
        logger.warning(f"MongoDB heatmap aggregation failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Fallback simulated heatmap (original logic preserved)
# ---------------------------------------------------------------------------

def _generate_heatmap_grid(hours: int, grid: int):
    """Gera dados de heatmap com base nos sensores locais (ou simulados)."""
    now = datetime.utcnow()
    cells = []
    for i in range(grid):
        for j in range(grid):
            # Gradiente térmico realista: mais quente no centro, mais frio nas bordas
            cx = grid / 2
            cy = grid / 2
            dist = math.sqrt((i - cx) ** 2 + (j - cy) ** 2)
            base_temp = 36.0 - (dist / (grid / 2)) * 4.0
            noise = random.uniform(-0.5, 0.5)
            temp = round(base_temp + noise, 1)
            cells.append(
                {
                    "x": i,
                    "y": j,
                    "temp": temp,
                    "density": max(
                        0,
                        round(1.0 - (dist / (grid / 2)) + random.uniform(-0.1, 0.1), 2),
                    ),
                }
            )

    # Pontos de referência de tempo (últimas `hours` horas)
    timeline = []
    for h in range(hours):
        ts = now - timedelta(hours=hours - h)
        timeline.append(
            {
                "ts": ts.isoformat() + "Z",
                "avg_temp": round(35.5 + random.uniform(-1.5, 1.5), 1),
            }
        )

    return {
        "grid": grid,
        "hours": hours,
        "cells": cells,
        "timeline": timeline,
        "source": "simulated",
        "generated_at": now.isoformat() + "Z",
    }


# ---------------------------------------------------------------------------
# Thermal anomalies from MongoDB detections
# ---------------------------------------------------------------------------

async def _get_thermal_anomalies_from_mongo(minutes: int) -> list | None:
    """
    Detects anomalies from real CV data: overcrowding zones and density outliers
    by querying the cv_heatmap_coords collection.
    """
    try:
        db = get_nosql_db()
        cutoff = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()

        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {
                "$project": {
                    "zone_x": {"$floor": {"$divide": ["$x", 160]}},
                    "zone_y": {"$floor": {"$divide": ["$y", 120]}},
                }
            },
            {
                "$group": {
                    "_id": {"zx": "$zone_x", "zy": "$zone_y"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]

        cursor = db["cv_heatmap_coords"].aggregate(pipeline)
        zone_counts = await cursor.to_list(length=10)

        if not zone_counts:
            return None

        max_count = zone_counts[0]["count"] if zone_counts else 1
        anomalies = []

        for i, z in enumerate(zone_counts):
            density = round(z["count"] / max_count, 2)
            zone_label = f"{chr(65 + int(z['_id']['zx']) % 26)}{int(z['_id']['zy']) + 1}"

            if density >= 0.7:
                anomalies.append({
                    "id": f"anomaly-mongo-{i+1}",
                    "type": "overcrowding" if density >= 0.85 else "hot_spot",
                    "severity": "warning" if density >= 0.85 else "info",
                    "zone": zone_label,
                    "density": density,
                    "detected_at": datetime.utcnow().isoformat() + "Z",
                    "description": (
                        f"Zona {zone_label}: concentração elevada de aves ({int(density * 100)}%)"
                        if density >= 0.85
                        else f"Zona {zone_label}: ponto quente detectado (densidade {int(density * 100)}%)"
                    ),
                    "source": "mongodb",
                })

        return anomalies if anomalies else None

    except Exception as exc:
        logger.warning(f"MongoDB anomaly query failed: {exc}")
        return None


def _generate_thermal_anomalies(minutes: int):
    """Retorna lista de anomalias térmicas detectadas nos últimos N minutos."""
    now = datetime.utcnow()
    anomalies = []

    # Simula anomalias baseadas em dados reais de sensores
    # Na produção, isso viria de queries na tabela thermal_events ou sensor_readings
    sample_anomalies = [
        {"type": "hot_spot", "severity": "warning", "zone": "A3", "temp": 38.5},
        {"type": "cold_zone", "severity": "info", "zone": "D1", "temp": 32.1},
        {"type": "overcrowding", "severity": "warning", "zone": "B2", "density": 0.92},
    ]

    for i, base in enumerate(sample_anomalies):
        ts = now - timedelta(minutes=random.randint(1, minutes))
        anomaly = {
            "id": f"anomaly-{i + 1}",
            "type": base["type"],
            "severity": base["severity"],
            "zone": base["zone"],
            "detected_at": ts.isoformat() + "Z",
            "description": _anomaly_description(base),
        }
        if "temp" in base:
            anomaly["temp"] = base["temp"]
        if "density" in base:
            anomaly["density"] = base["density"]
        anomalies.append(anomaly)

    return anomalies


def _anomaly_description(a: dict) -> str:
    if a["type"] == "hot_spot":
        return f"Zona {a['zone']}: temperatura acima do normal ({a.get('temp', '?')}°C)"
    if a["type"] == "cold_zone":
        return (
            f"Zona {a['zone']}: temperatura abaixo do esperado ({a.get('temp', '?')}°C)"
        )
    if a["type"] == "overcrowding":
        return f"Zona {a['zone']}: concentração elevada de aves ({int(a.get('density', 0) * 100)}%)"
    return f"Anomalia detectada na zona {a.get('zone', '?')}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/heatmap/3d")
async def heatmap_3d(
    hours: int = Query(default=1, ge=1, le=48),
    grid: int = Query(default=24, ge=8, le=64),
    user: UserContext = Depends(get_current_user),
):
    """Dados do heatmap térmico 3D para o Gêmeo Digital (reais da visão ou simulados)."""
    # Priority 1: Spatial accumulator (in-memory real-time)
    try:
        from src.core.state import spatial_accumulator
        if spatial_accumulator is not None:
            points_3d = spatial_accumulator.get_3d_points(grid_size=grid, hours=hours)
            if points_3d:
                return {
                    "grid": grid,
                    "hours": hours,
                    "cells": points_3d,
                    "source": "vision_spatial_accumulator",
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                }
    except Exception:
        pass

    # Priority 2: MongoDB aggregation (persistent CV data)
    mongo_data = await _generate_heatmap_from_mongo(hours, grid)
    if mongo_data:
        return mongo_data

    # Priority 3: Simulated fallback
    data = await run_in_threadpool(_generate_heatmap_grid, hours, grid)
    return data


@router.get("/thermal-anomalies/live")
async def thermal_anomalies_live(
    minutes: int = Query(default=15, ge=1, le=1440),
    user: UserContext = Depends(get_current_user),
):
    """Anomalias térmicas detectadas em tempo real."""
    # Try MongoDB first
    mongo_anomalies = await _get_thermal_anomalies_from_mongo(minutes)
    if mongo_anomalies:
        return {"count": len(mongo_anomalies), "items": mongo_anomalies, "source": "mongodb"}

    # Fallback to simulated
    anomalies = await run_in_threadpool(_generate_thermal_anomalies, minutes)
    return {"count": len(anomalies), "items": anomalies, "source": "simulated"}
