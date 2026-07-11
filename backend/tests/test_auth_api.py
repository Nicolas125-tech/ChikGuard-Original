import os

os.environ["SUPABASE_JWT_SECRET"] = "dummy_secret"
os.environ["ADMIN_PASSWORD"] = "testpassword"
os.environ["ADMIN_EMAIL"] = "test@example.com"
os.environ["JWT_SECRET_KEY"] = "testsecret"
os.environ["CORS_ALLOWED_ORIGINS"] = "*"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest

from app_flask_legacy import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    with app.test_client() as client:
        yield client


def test_accounts_me_invalid_session(client):
    """Testa a rota /api/accounts/me sem autenticacao para garantir que retorna 401."""
    response = client.get("/api/accounts/me")
    assert response.status_code == 401
    assert response.json == {"msg": "Sessão inválida"}
