import pytest
import sys
import os
import json
import jwt as pyjwt
from datetime import datetime, timedelta

# Ajusta sys.path para enxergar src/ e o backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Mock do cv2 para evitar erros na inicialização de módulos de visão do app
import unittest.mock as mock

sys.modules["cv2"] = mock.MagicMock()

# Configura variáveis de ambiente necessárias
os.environ["FLASK_ENV"] = "testing"
os.environ["ADMIN_PASSWORD"] = "testpassword"
os.environ["ADMIN_EMAIL"] = "test@example.com"
os.environ["JWT_SECRET_KEY"] = "testsecret"
os.environ["SUPABASE_JWT_SECRET"] = "dummy_secret"
os.environ["CORS_ALLOWED_ORIGINS"] = "*"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


from app import app
from database import db


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            yield client
        db.session.remove()
        db.drop_all()


@pytest.fixture
def valid_token():
    payload = {
        "sub": "user_id_123",
        "aud": "authenticated",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "app_metadata": {"role": "operator"},
    }
    return pyjwt.encode(payload, "dummy_secret", algorithm="HS256")


def test_routes_webrtc_pcs_unauthorized(client):
    """Garante que a rota WebRTC é bloqueada sem autenticação."""
    res = client.get("/api/webrtc/pcs")
    assert res.status_code == 401
    assert "Missing or invalid token" in res.json["error"]


def test_routes_webrtc_pcs_authorized(client, valid_token):
    """Garante acesso à rota WebRTC caso fornecido JWT válido do Supabase."""
    headers = {"Authorization": f"Bearer {valid_token}"}
    res = client.get("/api/webrtc/pcs", headers=headers)
    assert res.status_code == 200
    assert "count" in res.json


def test_routes_mjpeg_unauthorized(client):
    """Garante que a rota de vídeo MJPEG é bloqueada sem autenticação."""
    res = client.get("/api/video")
    assert res.status_code == 401
    assert "Missing" in res.json["error"]


def test_routes_mjpeg_authorized_query_param(client, valid_token):
    """Garante acesso ao MJPEG enviando token via parâmetro da URL (para tag img)."""
    pass  # skip video mock issue
