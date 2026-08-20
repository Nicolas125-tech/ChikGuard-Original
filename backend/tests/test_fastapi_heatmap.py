import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Need to mock cv2 before importing any application code
import unittest.mock as mock

sys.modules["cv2"] = mock.MagicMock()

from src.api.fastapi_heatmap import (
    router,
    _generate_heatmap_grid,
    _generate_thermal_anomalies,
)
from src.security.fastapi_auth import get_current_user, UserContext
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)


def override_get_current_user():
    return UserContext(user_id="test", role="admin", tenant_id=1)


app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)


def test_generate_heatmap_grid_standard():
    """Test standard grid generation with positive dimensions."""
    grid_size = 10
    hours = 2
    data = _generate_heatmap_grid(hours, grid_size)

    assert data["grid"] == grid_size
    assert data["hours"] == hours
    assert "cells" in data
    assert len(data["cells"]) == grid_size * grid_size
    assert "timeline" in data
    assert len(data["timeline"]) == hours
    assert "generated_at" in data

    # Verify cell properties and thermal gradient
    for cell in data["cells"]:
        assert "x" in cell
        assert "y" in cell
        assert "temp" in cell
        assert "density" in cell
        assert cell["density"] >= 0
        # Based on formula: base_temp = 36.0 - (dist / (grid / 2)) * 4.0
        # with noise between -0.5 and 0.5
        # The lowest temp is approx 36.0 - 4.0*sqrt(2) - 0.5 = 29.8
        # The highest temp is approx 36.0 + 0.5 = 36.5
        assert 25.0 <= cell["temp"] <= 40.0


def test_generate_heatmap_grid_zero():
    """Test edge cases with zero input. The function divides by grid/2, which causes ZeroDivisionError if grid is 0."""
    # Because of the loop `for i in range(grid):`, if grid is 0, the loop is never entered,
    # so ZeroDivisionError doesn't happen. It just returns empty lists.
    data = _generate_heatmap_grid(0, 0)
    assert data["grid"] == 0
    assert len(data["cells"]) == 0
    assert len(data["timeline"]) == 0


def test_generate_thermal_anomalies():
    minutes = 30
    anomalies = _generate_thermal_anomalies(minutes)

    assert isinstance(anomalies, list)
    assert len(anomalies) == 3  # based on the hardcoded sample_anomalies

    for anomaly in anomalies:
        assert "id" in anomaly
        assert "type" in anomaly
        assert "severity" in anomaly
        assert "zone" in anomaly
        assert "detected_at" in anomaly
        assert "description" in anomaly


def test_heatmap_3d_endpoint():
    response = client.get("/api/heatmap/3d?hours=3&grid=16")
    assert response.status_code == 200

    data = response.json()
    assert data["grid"] == 16
    assert data["hours"] == 3
    assert len(data["cells"]) == 16 * 16
    assert len(data["timeline"]) == 3


def test_heatmap_3d_endpoint_defaults():
    response = client.get("/api/heatmap/3d")
    assert response.status_code == 200

    data = response.json()
    assert data["grid"] == 24
    assert data["hours"] == 1


def test_heatmap_3d_endpoint_validation_errors():
    # Test grid boundaries (ge=8, le=64)
    response = client.get("/api/heatmap/3d?grid=7")
    assert response.status_code == 422

    response = client.get("/api/heatmap/3d?grid=65")
    assert response.status_code == 422

    # Test hours boundaries (ge=1, le=48)
    response = client.get("/api/heatmap/3d?hours=0")
    assert response.status_code == 422

    response = client.get("/api/heatmap/3d?hours=49")
    assert response.status_code == 422


def test_thermal_anomalies_live_endpoint():
    response = client.get("/api/thermal-anomalies/live?minutes=20")
    assert response.status_code == 200

    data = response.json()
    assert "count" in data
    assert "items" in data
    assert data["count"] == len(data["items"])
    assert data["count"] == 3


def test_thermal_anomalies_live_validation_errors():
    # Test minutes boundaries (ge=1, le=1440)
    response = client.get("/api/thermal-anomalies/live?minutes=0")
    assert response.status_code == 422

    response = client.get("/api/thermal-anomalies/live?minutes=1441")
    assert response.status_code == 422


def test_anomaly_description():
    """Test the internal helper for generating anomaly descriptions."""
    from src.api.fastapi_heatmap import _anomaly_description

    desc = _anomaly_description({"type": "hot_spot", "zone": "A1", "temp": 39.0})
    assert "Zona A1" in desc
    assert "acima do normal" in desc
    assert "39.0" in desc

    desc = _anomaly_description({"type": "cold_zone", "zone": "B2", "temp": 30.5})
    assert "Zona B2" in desc
    assert "abaixo do esperado" in desc
    assert "30.5" in desc

    desc = _anomaly_description({"type": "overcrowding", "zone": "C3", "density": 0.95})
    assert "Zona C3" in desc
    assert "95%" in desc

    desc = _anomaly_description({"type": "unknown", "zone": "D4"})
    assert "Anomalia detectada na zona D4" in desc
