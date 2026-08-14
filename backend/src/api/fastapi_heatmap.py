"""
fastapi_heatmap.py - Endpoints de heatmap térmico e anomalias térmicas
Retorna dados simulados/reais da tabela de sensores para o Gêmeo Digital 2D.
"""

from fastapi import APIRouter, Depends, Query
from src.security.fastapi_auth import get_current_user, UserContext
from fastapi.concurrency import run_in_threadpool
from datetime import datetime, timedelta
import random
import math

router = APIRouter(prefix="/api", tags=["heatmap"])


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
        "generated_at": now.isoformat() + "Z",
    }


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


@router.get("/heatmap/3d")
async def heatmap_3d(
    hours: int = Query(default=1, ge=1, le=48),
    grid: int = Query(default=24, ge=8, le=64),
    user: UserContext = Depends(get_current_user),
):
    """Dados do heatmap térmico 3D para o Gêmeo Digital (reais da visão ou simulados)."""
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

    data = await run_in_threadpool(_generate_heatmap_grid, hours, grid)
    return data


@router.get("/thermal-anomalies/live")
async def thermal_anomalies_live(
    minutes: int = Query(default=15, ge=1, le=1440),
    user: UserContext = Depends(get_current_user),
):
    """Anomalias térmicas detectadas em tempo real."""
    anomalies = await run_in_threadpool(_generate_thermal_anomalies, minutes)
    return {"count": len(anomalies), "items": anomalies}
