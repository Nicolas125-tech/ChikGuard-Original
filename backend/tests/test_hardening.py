import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
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
    response = client.get("/api/test-route", environ_base={"REMOTE_ADDR": "192.168.1.100"})
    assert response.headers.get("Server") == "Secure-Gateway"
    assert "X-Powered-By" not in response.headers


def test_honeypot_path_blocking(client):
    """Verifica se caminhos de honeypot bloqueiam o IP e retornam 403."""
    # 1. Tentar acessar um caminho honeypot típico (ex: /wp-admin)
    response = client.get("/wp-admin", environ_base={"REMOTE_ADDR": "192.168.1.100"})
    assert response.status_code == 403
    data = json.loads(response.data)
    assert data["code"] == "HONEYPOT_TRIGGERED"

    # 2. Verificar se o IP foi incluído na blacklist
    # O cliente de teste do Flask tem remote_addr = '127.0.0.1' por padrão
    assert "192.168.1.100" in BLACKLISTED_IPS

    # 3. Próxima requisição normal do mesmo IP deve ser rejeitada imediatamente
    with patch("time.sleep") as mock_sleep:
        response2 = client.get("/api/test-route", environ_base={"REMOTE_ADDR": "192.168.1.100"})
        assert response2.status_code == 403
        data2 = json.loads(response2.data)
        assert data2["code"] == "IP_BLACKLISTED"
        mock_sleep.assert_called_once()  # Tarpit deve ser ativado


def test_sqli_query_parameter_blocking(client):
    """Verifica se tentativas de SQL Injection nos parâmetros da query são rejeitadas."""
    response = client.get("/api/test-route?search='+OR+'1'='1", environ_base={"REMOTE_ADDR": "192.168.1.100"})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["code"] == "SUSPICIOUS_PAYLOAD"


def test_xss_json_payload_blocking(client):
    """Verifica se tentativas de XSS no corpo do JSON são rejeitadas."""
    payload = {"comment": "<script>alert('hack')</script>"}
    response = client.post(
        "/api/test-route", environ_base={"REMOTE_ADDR": "192.168.1.100"}, data=json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["code"] == "SUSPICIOUS_PAYLOAD"


@patch("src.security.hardening.RATE_LIMIT_MAX", 3)
def test_rate_limiting_trigger(client):
    """Verifica se o rate limiter temporário bloqueia acessos rápidos de um mesmo IP."""
    # Fazer 3 requisições normais (dentro do limite mockado de 3)
    for _ in range(3):
        response = client.get("/api/test-route", environ_base={"REMOTE_ADDR": "192.168.1.100"})
        assert response.status_code == 200

    # A 4ª requisição deve violar o limite, gerando bloqueio
    with patch("time.sleep") as mock_sleep:
        response_blocked = client.get("/api/test-route", environ_base={"REMOTE_ADDR": "192.168.1.100"})
        assert response_blocked.status_code == 429
        data = json.loads(response_blocked.data)
        assert data["code"] == "RATE_LIMIT_EXCEEDED"
        mock_sleep.assert_called_once()

@patch("src.security.hardening.logger.error")
@patch("src.security.hardening.time.time")
def test_blacklist_ip_function(mock_time, mock_logger):
    """Verifica o funcionamento direto da função blacklist_ip, ignorando localhost e registrando ips externos."""
    from src.security.hardening import blacklist_ip, BLOCK_DURATION_SEC, BLACKLISTED_IPS

    # Configura o mock do time para um valor fixo
    current_time = 1000.0
    mock_time.return_value = current_time

    # Testa IP válido
    ip_to_block = "192.168.0.50"
    reason = "Test Block"

    # Chama a função
    blacklist_ip(ip_to_block, reason)

    # Verifica se foi adicionado ao dicionário com o offset correto
    assert ip_to_block in BLACKLISTED_IPS
    assert BLACKLISTED_IPS[ip_to_block] == current_time + BLOCK_DURATION_SEC

    # Verifica se o log foi gerado
    mock_logger.assert_called_once_with(f"[SECURITY-ALERT] IP {ip_to_block} adicionado à lista negra. Motivo: {reason}")
    mock_logger.reset_mock()

    # Testa IP de localhost (IPv4) - não deve ser adicionado
    ip_localhost = "127.0.0.1"
    blacklist_ip(ip_localhost, "Should be ignored")
    assert ip_localhost not in BLACKLISTED_IPS
    mock_logger.assert_not_called()

    # Testa IP de localhost (IPv6) - não deve ser adicionado
    ip_ipv6_localhost = "::1"
    blacklist_ip(ip_ipv6_localhost, "Should be ignored")
    assert ip_ipv6_localhost not in BLACKLISTED_IPS
    mock_logger.assert_not_called()

from src.security.hardening import check_input_payload, validate_blacklisted_ip, validate_honeypots

@pytest.mark.parametrize("payload,expected", [
    ("", True),
    (None, True),
    ("safe regular text", True),
    ("user@email.com", True),
    ("12345", True),
    ("'<script>alert(\"xss\")</script>'", False),
    ("javascript:alert(1)", False),
    ("<iframe src='hack.com'>", False),
    ("onerror=alert(1)", False),
    ("onload=evil()", False),
    ("' OR '1'='1", False),
    ("UNION SELECT *", False),
    ("DROP TABLE users", False),
    ("INSERT INTO data", False),
    ("admin' --", False),
    ("/* secret */", False),
    ("select username from", False)
])
def test_check_input_payload(payload, expected):
    """Verifica se check_input_payload identifica corretamente SQLi e XSS em várias strings."""
    assert check_input_payload(payload) == expected

def test_validate_blacklisted_ip_not_blocked(secure_app):
    """Verifica se IPs não bloqueados retornam None."""
    with secure_app.app_context():
        assert validate_blacklisted_ip("192.168.1.100") is None
        assert validate_blacklisted_ip("127.0.0.1") is None

@patch("src.security.hardening.enforce_tarpit")
def test_validate_blacklisted_ip_blocked(mock_tarpit, secure_app):
    """Verifica se IPs bloqueados ativam o tarpit e retornam resposta de erro (403)."""
    from src.security.hardening import blacklist_ip
    blacklist_ip("192.168.1.200", "test reason")

    with secure_app.app_context():
        response_tuple = validate_blacklisted_ip("192.168.1.200")
        assert response_tuple is not None
        response, status_code = response_tuple
        assert status_code == 403
        assert response.json["code"] == "IP_BLACKLISTED"
        mock_tarpit.assert_called_once()

@patch("src.security.hardening.enforce_tarpit")
def test_validate_honeypots_triggered(mock_tarpit, secure_app):
    """Verifica se caminhos de honeypot são detectados, banindo o IP e retornando erro 403."""
    from src.security.hardening import BLACKLISTED_IPS
    ip = "192.168.1.55"
    with secure_app.app_context():
        response_tuple = validate_honeypots(ip, "/wp-admin/login.php")
        assert response_tuple is not None
        response, status_code = response_tuple
        assert status_code == 403
        assert response.json["code"] == "HONEYPOT_TRIGGERED"
        assert ip in BLACKLISTED_IPS
        mock_tarpit.assert_called_once()

def test_validate_honeypots_safe(secure_app):
    """Verifica se caminhos normais passam na validação de honeypot."""
    with secure_app.app_context():
        assert validate_honeypots("192.168.1.100", "/api/v1/users") is None
