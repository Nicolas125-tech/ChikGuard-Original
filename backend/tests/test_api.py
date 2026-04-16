import pytest
from unittest.mock import patch, MagicMock

try:
    from flask import Flask
    from src.api.routes import create_api_blueprint
except ImportError:
    pytest.skip("Flask not installed in test env", allow_module_level=True)

@pytest.fixture
def app():
    app = Flask(__name__)
    deps = {
        "get_global_frame": lambda: None,
        "stream_frame_interval_sec": 0.1,
        "stream_jpeg_quality": 80
    }
    bp = create_api_blueprint(deps)
    app.register_blueprint(bp)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_webrtc_offer_missing_params(client):
    response = client.post('/api/webrtc/offer', json={})
    assert response.status_code == 400
    assert b"Missing sdp or type" in response.data

@patch('src.api.routes.RTCPeerConnection')
def test_webrtc_pcs_count(mock_rtc, client):
    response = client.get('/api/webrtc/pcs')
    assert response.status_code == 200
    assert response.json["count"] >= 0
