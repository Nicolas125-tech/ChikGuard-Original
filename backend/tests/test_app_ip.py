import pytest
from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix


@pytest.fixture
def app():
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=0)
    return app


def test_request_ip_direct_untrusted(app):
    client = app.test_client()

    @app.route("/")
    def index():
        return request.remote_addr or ""

    res = client.get("/", environ_base={"REMOTE_ADDR": "8.8.8.8"})
    assert res.text == "8.8.8.8"


def test_request_ip_spoof_prevented(app):
    client = app.test_client()

    @app.route("/")
    def index():
        return request.remote_addr or ""

    # Request from trusted proxy, client is 8.8.8.8
    res = client.get(
        "/", headers={"X-Forwarded-For": "8.8.8.8"}, environ_base={"REMOTE_ADDR": "10.0.0.1"}
    )
    assert res.text == "8.8.8.8"

    # With x_for=1, ProxyFix picks the last IP as the client (8.8.8.8), preventing 1.1.1.1 spoof
    res = client.get(
        "/",
        headers={"X-Forwarded-For": "1.1.1.1, 8.8.8.8"},
        environ_base={"REMOTE_ADDR": "10.0.0.1"},
    )
    assert res.text == "8.8.8.8"
