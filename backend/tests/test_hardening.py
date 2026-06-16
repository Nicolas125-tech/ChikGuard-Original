import json
from unittest.mock import patch

import pytest
from flask import Flask, jsonify

from src.security.hardening import (
    BLACKLISTED_IPS,
    IP_REQUESTS,
    setup_hardening,
)


@pytest.fixture
def secure_app():
    app = Flask("secure_test_app")
    setup_hardening(app)

    @app.route("/api/test-route", methods=["GET", "POST"])
    def test_route():
        return jsonify({"status": "ok"})

    # Reset blacklists and request counters between tests
    BLACKLISTED_IPS.clear()
    IP_REQUESTS.clear()

    return app


@pytest.fixture
def client(secure_app):
    return secure_app.test_client()


def test_server_header_masking(client):
    """Verifica se o cabeçalho 'Server' é mascarado para evitar banner grabbing."""
    response = client.get("/api/test-route")
    assert response.headers.get("Server") == "Secure-Gateway"
    assert "X-Powered-By" not in response.headers


def test_honeypot_path_blocking(client):
    """Verifica se caminhos de honeypot bloqueiam o IP e retornam 403."""
    # 1. Tentar acessar um caminho honeypot típico (ex: /wp-admin)
    response = client.get("/wp-admin")
    assert response.status_code == 403
    data = json.loads(response.data)
    assert data["code"] == "HONEYPOT_TRIGGERED"

    # 2. Verificar se o IP foi incluído na blacklist
    # O cliente de teste do Flask tem remote_addr = '127.0.0.1' por padrão
    assert "127.0.0.1" in BLACKLISTED_IPS

    # 3. Próxima requisição normal do mesmo IP deve ser rejeitada imediatamente
    with patch("time.sleep") as mock_sleep:
        response2 = client.get("/api/test-route")
        assert response2.status_code == 403
        data2 = json.loads(response2.data)
        assert data2["code"] == "IP_BLACKLISTED"
        mock_sleep.assert_called_once()  # Tarpit deve ser ativado


def test_sqli_query_parameter_blocking(client):
    """Verifica se tentativas de SQL Injection nos parâmetros da query são rejeitadas."""
    response = client.get("/api/test-route?search='+OR+'1'='1")
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["code"] == "SUSPICIOUS_PAYLOAD"


def test_xss_json_payload_blocking(client):
    """Verifica se tentativas de XSS no corpo do JSON são rejeitadas."""
    payload = {"comment": "<script>alert('hack')</script>"}
    response = client.post(
        "/api/test-route", data=json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["code"] == "SUSPICIOUS_PAYLOAD"


@patch("src.security.hardening.RATE_LIMIT_MAX", 3)
def test_rate_limiting_trigger(client):
    """Verifica se o rate limiter temporário bloqueia acessos rápidos de um mesmo IP."""
    # Fazer 3 requisições normais (dentro do limite mockado de 3)
    for _ in range(3):
        response = client.get("/api/test-route")
        assert response.status_code == 200

    # A 4ª requisição deve violar o limite, gerando bloqueio
    with patch("time.sleep") as mock_sleep:
        response_blocked = client.get("/api/test-route")
        assert response_blocked.status_code == 429
        data = json.loads(response_blocked.data)
        assert data["code"] == "RATE_LIMIT_EXCEEDED"
        mock_sleep.assert_called_once()
