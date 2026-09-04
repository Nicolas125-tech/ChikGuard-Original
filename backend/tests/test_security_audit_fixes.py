import os
import sys
from unittest.mock import MagicMock, patch
import pytest

os.environ["SUPABASE_JWT_SECRET"] = os.environ.get("SUPABASE_JWT_SECRET", "dummy_secret_dummy_secret_dummy_secret_for_tests_32bytes")

if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
sys.modules["cv2"] = MagicMock()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.security.fastapi_auth import UserContext, get_current_user
from src.security.headers import FastAPISecurityHeadersMiddleware
from src.presentation.api.fastapi_sensors import router as sensors_router
from src.presentation.api.fastapi_accounts import router as accounts_router
from src.infrastructure.db.session import get_db, get_async_db

# Create test app with security middleware and routers
app = FastAPI()
app.add_middleware(FastAPISecurityHeadersMiddleware)
app.include_router(sensors_router)
app.include_router(accounts_router)

client = TestClient(app)

def test_security_headers_present():
    """Valida se todos os cabeçalhos de segurança obrigatórios estão presentes."""
    response = client.get("/docs")
    assert "x-frame-options" in response.headers
    assert response.headers["x-frame-options"] == "DENY"
    assert "x-content-type-options" in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" in response.headers
    assert "server" in response.headers
    assert response.headers["server"] == "Secure-Edge-Node"

def test_sensor_ingest_forbidden_for_viewer():
    """Valida que usuários 'viewer' NÃO podem injetar dados que acionem atuadores."""
    def viewer_user():
        return UserContext(user_id="viewer-1", role="viewer", tenant_id=1)

    app.dependency_overrides[get_current_user] = viewer_user
    try:
        payload = {
            "temperature_c": 38.0,
            "humidity_pct": 80.0,
            "ammonia_ppm": 25.0,
            "feed_level_pct": 50.0,
            "water_level_pct": 50.0,
            "source": "malicious_spoof"
        }
        response = client.post("/api/sensors/ingest", json=payload)
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)

def test_sensor_ingest_allowed_for_operator():
    """Valida que usuários com role 'operator' podem injetar telemetria."""
    def operator_user():
        return UserContext(user_id="operator-1", role="operator", tenant_id=1)

    mock_db = MagicMock()
    app.dependency_overrides[get_current_user] = operator_user
    app.dependency_overrides[get_async_db] = lambda: mock_db
    try:
        payload = {
            "temperature_c": 24.5,
            "humidity_pct": 60.0,
            "ammonia_ppm": 5.0,
            "feed_level_pct": 80.0,
            "water_level_pct": 90.0,
            "source": "legit_node"
        }
        with patch("src.presentation.api.fastapi_sensors.persist_sensor_reading"), \
             patch("src.presentation.api.fastapi_sensors.evaluate_sensor_alerts"):
            response = client.post("/api/sensors/ingest", json=payload)
            assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_async_db, None)

def test_ensure_profile_rejects_unauthorized_user_id():
    """Valida que um usuário não pode criar/sincronizar perfis para IDs de outros usuários."""
    def regular_user():
        return UserContext(user_id="user-123", role="viewer", tenant_id=1)

    app.dependency_overrides[get_current_user] = regular_user
    try:
        payload = {
            "user_id": "different-target-id-456",
            "email": "victim@test.com",
            "full_name": "Injected Name"
        }
        response = client.post("/api/accounts/ensure-profile", json=payload)
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
