import os
import pytest
import jwt
from flask import Flask

# Set environment variables for testing
os.environ["SUPABASE_JWT_SECRET"] = os.environ.get("SUPABASE_JWT_SECRET", "dummy_secret_dummy_secret_dummy_secret")
os.environ["ADMIN_PASSWORD"] = "testpassword"
os.environ["ADMIN_EMAIL"] = "test@example.com"
os.environ["JWT_SECRET_KEY"] = "testsecret"
os.environ["CORS_ALLOWED_ORIGINS"] = "*"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import unittest.mock as mock

# mock cv2 before importing any application code
sys_modules_mock = mock.patch.dict("sys.modules", {"cv2": mock.MagicMock()})
sys_modules_mock.start()

from src.api.sync_api import create_sync_blueprint

@pytest.fixture
def mock_deps():
    mock_db = mock.MagicMock()
    mock_SyncQueueItem = mock.MagicMock()
    return {
        "db": mock_db,
        "SyncQueueItem": mock_SyncQueueItem
    }

@pytest.fixture
def test_app(mock_deps):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    bp = create_sync_blueprint(mock_deps)
    app.register_blueprint(bp)

    return app

@pytest.fixture
def client(test_app):
    with test_app.test_client() as client:
        yield client

@pytest.fixture
def auth_headers():
    token = jwt.encode(
        {
            "sub": "user_id_test",
            "aud": "authenticated",
            "app_metadata": {
                "role": "admin",
                "tenant_id": 1
            }
        },
        os.environ["SUPABASE_JWT_SECRET"],
        algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}

def test_sync_status_unauthorized(client):
    """Test GET /api/sync/status without auth"""
    response = client.get("/api/sync/status")
    assert response.status_code == 401

def test_sync_pending_unauthorized(client):
    """Test GET /api/sync/pending without auth"""
    response = client.get("/api/sync/pending")
    assert response.status_code == 401

def test_sync_ack_unauthorized(client):
    """Test POST /api/sync/ack without auth"""
    response = client.post("/api/sync/ack")
    assert response.status_code == 401

def test_sync_pending_authorized(client, auth_headers):
    """Test GET /api/sync/pending with valid auth"""
    response = client.get("/api/sync/pending", headers=auth_headers)
    assert response.status_code == 200
    assert response.json["pending"] == 0

def test_sync_ack_authorized(client, auth_headers):
    """Test POST /api/sync/ack with valid auth"""
    response = client.post("/api/sync/ack", headers=auth_headers)
    assert response.status_code == 200
    assert response.json["status"] == "acknowledged"

def test_sync_status_offline(client, auth_headers):
    """Test GET /api/sync/status when db or SyncQueueItem is None"""
    # Create another app with None deps
    app2 = Flask(__name__)
    app2.config["TESTING"] = True
    bp2 = create_sync_blueprint({"db": None, "SyncQueueItem": None})
    app2.register_blueprint(bp2)
    with app2.test_client() as c2:
        response = c2.get("/api/sync/status", headers=auth_headers)
        assert response.status_code == 200
        assert response.json["status"] == "offline"
        assert response.json["pending_items"] == 0

def test_sync_status_online(client, mock_deps, auth_headers):
    """Test GET /api/sync/status with valid auth and no pending items"""
    mock_query = mock.MagicMock()
    mock_filter_by = mock.MagicMock()
    mock_filter_by.count.return_value = 0
    mock_query.filter_by.return_value = mock_filter_by
    mock_deps["SyncQueueItem"].query = mock_query

    response = client.get("/api/sync/status", headers=auth_headers)
    assert response.status_code == 200
    assert response.json["status"] == "online"
    assert response.json["pending_items"] == 0
    mock_deps["SyncQueueItem"].query.filter_by.assert_called_with(synced=False)

def test_sync_status_with_pending_items(client, mock_deps, auth_headers):
    """Test GET /api/sync/status with pending sync items"""
    mock_query = mock.MagicMock()
    mock_filter_by = mock.MagicMock()
    mock_filter_by.count.return_value = 5
    mock_query.filter_by.return_value = mock_filter_by
    mock_deps["SyncQueueItem"].query = mock_query

    response = client.get("/api/sync/status", headers=auth_headers)
    assert response.status_code == 200
    assert response.json["status"] == "online"
    assert response.json["pending_items"] == 5
    mock_deps["SyncQueueItem"].query.filter_by.assert_called_with(synced=False)

def test_sync_status_exception(client, mock_deps, auth_headers):
    """Test GET /api/sync/status when an exception occurs"""
    mock_query = mock.MagicMock()
    mock_query.filter_by.side_effect = Exception("Test Database Exception")
    mock_deps["SyncQueueItem"].query = mock_query

    response = client.get("/api/sync/status", headers=auth_headers)
    assert response.status_code == 500
    assert response.json["status"] == "error"
    assert response.json["message"] == "Ocorreu um erro interno de sincronizacao."
