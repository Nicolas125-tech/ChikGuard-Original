import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import sys
import os

# Ensure modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock cv2 before anything else
sys.modules["cv2"] = MagicMock()

from src.api.fastapi_cameras import router
from src.security.fastapi_auth import get_current_user, UserContext
from src.db.session import get_db
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)

def override_get_current_user():
    return UserContext(user_id="test", role="admin", tenant_id=1)

app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

def test_get_cameras():
    mock_db = MagicMock()
    mock_camera_1 = MagicMock()
    mock_camera_1.to_dict.return_value = {
        "id": 1,
        "tenant_id": 1,
        "camera_id": "cam-1",
        "name": "Camera 1",
        "connection_type": "usb",
        "connection_url": "",
        "status": "online",
        "created_at": "2023-01-01 10:00:00"
    }

    mock_camera_2 = MagicMock()
    mock_camera_2.to_dict.return_value = {
        "id": 2,
        "tenant_id": 1,
        "camera_id": "cam-2",
        "name": "Camera 2",
        "connection_type": "rtsp",
        "connection_url": "rtsp://localhost:8554/stream",
        "status": "offline",
        "created_at": "2023-01-02 10:00:00"
    }

    mock_db.query.return_value.order_by.return_value.all.return_value = [mock_camera_1, mock_camera_2]

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    import src.core.state as state
    original_active_camera_id = state.active_camera_id
    state.active_camera_id = "cam-1"

    try:
        response = client.get("/api/cameras")

        assert response.status_code == 200

        data = response.json()
        assert data["active_camera_id"] == "cam-1"
        assert data["count"] == 2
        assert len(data["items"]) == 2

        assert data["items"][0]["camera_id"] == "cam-1"
        assert data["items"][0]["name"] == "Camera 1"
        assert data["items"][1]["camera_id"] == "cam-2"
        assert data["items"][1]["connection_type"] == "rtsp"
    finally:
        state.active_camera_id = original_active_camera_id
