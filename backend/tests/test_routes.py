import pytest
from flask import Flask
from unittest.mock import MagicMock, patch
import sys
import os
import asyncio

# Ensure modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Setup environment variables needed by app modules
os.environ["SUPABASE_JWT_SECRET"] = "dummy_secret_dummy_secret_dummy_secret_for_testing_32b"

# Mock external dependencies
sys.modules["cv2"] = MagicMock()
sys.modules["aiortc"] = MagicMock()
sys.modules["aiortc.contrib.media"] = MagicMock()
sys.modules["av"] = MagicMock()

# Patch require_auth before importing routes
import src.security.auth
def dummy_require_auth(*args, **kwargs):
    def decorator(f):
        import functools
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated
    return decorator
src.security.auth.require_auth = dummy_require_auth
import sys
if 'src.api.routes' in sys.modules:
    sys.modules.pop('src.api.routes')

from src.api.routes import create_api_blueprint

@pytest.fixture
def deps():
    return {
        "get_global_frame": MagicMock(return_value="mock_frame"),
        "stream_frame_interval_sec": 0.1,
        "stream_jpeg_quality": 80,
    }

@pytest.fixture
def app(deps):
    app = Flask(__name__)
    bp = create_api_blueprint(deps)
    app.register_blueprint(bp)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_blueprint_initialization(app):
    """Test that the blueprint initializes and registers the correct routes."""
    rules = [rule.rule for rule in app.url_map.iter_rules()]
    assert "/api/video" in rules
    assert "/api/webrtc/offer" in rules
    assert "/api/webrtc/pcs" in rules

def test_webrtc_pcs_route(client):
    """Test the /api/webrtc/pcs route."""
    response = client.get("/api/webrtc/pcs")
    assert response.status_code == 200
    assert "count" in response.json

def test_webrtc_offer_route_missing_params(client):
    """Test the /api/webrtc/offer route with missing parameters."""
    response = client.post("/api/webrtc/offer", json={})
    assert response.status_code == 400
    assert response.json == {"error": "Missing sdp or type in request body"}

    response = client.post("/api/webrtc/offer", json={"sdp": "something"})
    assert response.status_code == 400

    response = client.post("/api/webrtc/offer", json={"type": "offer"})
    assert response.status_code == 400

@patch('src.api.routes.asyncio.run_coroutine_threadsafe')
def test_webrtc_offer_route_success(mock_run_coroutine_threadsafe, client):
    """Test the /api/webrtc/offer route with successful connection."""
    # Mock the future returned by run_coroutine_threadsafe
    mock_future = MagicMock()
    mock_answer = MagicMock()
    mock_answer.sdp = "mock_sdp_answer"
    mock_answer.type = "answer"
    mock_future.result.return_value = mock_answer

    # Track submitted coroutines so we can clean them up to avoid warnings
    submitted_coros = []

    def side_effect(coro, loop):
        submitted_coros.append(coro)
        return mock_future

    mock_run_coroutine_threadsafe.side_effect = side_effect

    response = client.post("/api/webrtc/offer", json={"sdp": "mock_sdp_offer", "type": "offer"})
    assert response.status_code == 200
    assert response.json == {"sdp": "mock_sdp_answer", "type": "answer"}

    # Clean up the unawaited coroutine to avoid RuntimeWarning
    for coro in submitted_coros:
        coro.close()

@patch('src.api.routes.asyncio.run_coroutine_threadsafe')
def test_webrtc_offer_route_exception(mock_run_coroutine_threadsafe, client):
    """Test the /api/webrtc/offer route with internal exception."""
    # Mock the future to raise an exception
    mock_future = MagicMock()
    mock_future.result.side_effect = Exception("Test exception")

    # Track submitted coroutines so we can clean them up to avoid warnings
    submitted_coros = []

    def side_effect(coro, loop):
        submitted_coros.append(coro)
        return mock_future

    mock_run_coroutine_threadsafe.side_effect = side_effect

    response = client.post("/api/webrtc/offer", json={"sdp": "mock_sdp_offer", "type": "offer"})
    assert response.status_code == 500
    assert response.json == {"error": "Ocorreu um erro interno ao processar a oferta WebRTC"}

    # Clean up the unawaited coroutine to avoid RuntimeWarning
    for coro in submitted_coros:
        coro.close()
