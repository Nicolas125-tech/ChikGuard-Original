import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock cv2 before anything else
sys.modules["cv2"] = MagicMock()

from src.api.fastapi_health import router
from src.security.fastapi_auth import get_current_user, UserContext
from src.db.session import get_db
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)

def override_get_current_user():
    return UserContext(user_id="test", role="admin", tenant_id=1)

app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

@patch('src.api.fastapi_health.psutil')
def test_system_health_online(mock_psutil):
    # Setup mock for psutil
    mock_psutil.cpu_percent.return_value = 15.0

    mock_mem = MagicMock()
    mock_mem.percent = 50.0
    mock_mem.total = 1000
    mock_mem.used = 500
    mock_psutil.virtual_memory.return_value = mock_mem

    mock_disk = MagicMock()
    mock_disk.percent = 60.0
    mock_disk.total = 2000
    mock_disk.used = 1200
    mock_psutil.disk_usage.return_value = mock_disk

    # Mock DB session
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    response = client.get("/api/health/system")
    assert response.status_code == 200

    data = response.json()
    assert data["cpu"] == 15.0
    assert data["memory"] == 50.0
    assert data["memory_total"] == 1000
    assert data["memory_used"] == 500
    assert data["disk"] == 60.0
    assert data["disk_total"] == 2000
    assert data["disk_used"] == 1200
    assert "uptime_seconds" in data
    assert data["database"] == "Online"
    import src.core.state as state

    # Test Offline
    state.get_global_frame = state._default_get_global_frame
    response_offline = client.get("/api/health/system")
    assert response_offline.json()["cv_pipeline"] == "Offline"

    # Test Online
    state.get_global_frame = lambda: "Real Frame"
    response_online = client.get("/api/health/system")
    assert response_online.json()["cv_pipeline"] == "Online"

    # Cleanup
    state.get_global_frame = state._default_get_global_frame

    assert mock_db.execute.call_count == 3

@patch('src.api.fastapi_health.psutil')
def test_system_health_db_offline(mock_psutil):
    # Setup mock for psutil
    mock_psutil.cpu_percent.return_value = 15.0
    mock_psutil.virtual_memory.return_value = MagicMock(percent=50.0, total=1000, used=500)
    mock_psutil.disk_usage.return_value = MagicMock(percent=60.0, total=2000, used=1200)

    # Mock DB session to raise an exception
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("DB Error")

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    response = client.get("/api/health/system")
    assert response.status_code == 200

    data = response.json()
    assert data["database"] == "Offline"

@patch('src.api.fastapi_health.psutil')
def test_system_health_db_check_error_path(mock_psutil):
    # Setup mock for psutil
    mock_psutil.cpu_percent.return_value = 20.0
    mock_psutil.virtual_memory.return_value = MagicMock(percent=40.0, total=1000, used=400)
    mock_psutil.disk_usage.return_value = MagicMock(percent=50.0, total=2000, used=1000)

    # Mock DB session to raise an exception upon execute()
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("Simulated DB Connection Failure")

    def override_get_db_failure():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db_failure

    response = client.get("/api/health/system")
    assert response.status_code == 200
    assert response.json()["database"] == "Offline"
