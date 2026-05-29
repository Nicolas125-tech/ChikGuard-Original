import pytest
import time
from flask import Flask
from src.security.rate_limiter import setup_rate_limiting
from src.api.auth import create_auth_blueprint


@pytest.fixture
def auth_app():
    app = Flask("auth_test_app")

    # Configure Rate Limiting First
    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"
    setup_rate_limiting(app)

    class MockQuery:
        def filter_by(self, **kwargs):
            return self

        def first(self):
            return None

    class MockAccount:
        query = MockQuery()

    # Mock deps
    deps = {
        "guard_critical_action": lambda *args, **kwargs: (True, None),
        "get_current_account": lambda: None,
        "audit": lambda *args, **kwargs: None,
        "bcrypt": None,
        "db": None,
        "Account": MockAccount,
        "RolePermission": None,
        "create_access_token": lambda *args, **kwargs: "token",
        "request_ip": lambda: "127.0.0.1",
        "utcnow": time.time
    }

    bp = create_auth_blueprint(deps)
    app.register_blueprint(bp)

    return app


@pytest.fixture
def client(auth_app):
    return auth_app.test_client()


def test_auth_login_rate_limiting(client):
    """Verifica se o rate limiter protege a rota de login."""
    # Fazer 5 requisições normais (limite no decorator é 5 per minute)
    for _ in range(5):
        response = client.post("/api/login", json={"username": "test", "password": "pwd"})
        assert response.status_code == 401  # Deve falhar login, mas não rate limit

    # A 6ª requisição deve violar o limite, gerando bloqueio
    response_blocked = client.post("/api/login", json={"username": "test", "password": "pwd"})
    assert response_blocked.status_code == 429
    pass
