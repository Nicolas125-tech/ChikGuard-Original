import pytest
from fastapi.testclient import TestClient
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Need to mock cv2 before importing any application code
import unittest.mock as mock
sys.modules["cv2"] = mock.MagicMock()

from main import fastapi_app
from src.core.state import live_birds
from src.api.fastapi_birds import BIRD_LIVE_TTL_SEC
from src.security.fastapi_auth import get_current_user, UserContext

# Bypass auth for tests
def override_get_current_user():
    return UserContext(user_id="test_user", role="admin", tenant_id=1)

fastapi_app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(fastapi_app)

def test_live_birds_ttl_filtering():
    """
    Test that birds older than BIRD_LIVE_TTL_SEC are excluded from the response.
    """
    now = time.time()

    # Inject test data directly into the state dictionary
    live_birds.clear()

    # 1. Bird that should be included (recent)
    live_birds["1"] = {
        "conf": 0.95,
        "box": [10, 10, 20, 20],
        "track_id": 1,
        "last_seen": now - (BIRD_LIVE_TTL_SEC - 1.0), # 1 second before TTL
        "species": "bird",
        "species_label": "AVE"
    }

    # 2. Bird that should be excluded (expired)
    live_birds["2"] = {
        "conf": 0.85,
        "box": [30, 30, 40, 40],
        "track_id": 2,
        "last_seen": now - (BIRD_LIVE_TTL_SEC + 1.0), # 1 second after TTL
        "species": "bird",
        "species_label": "AVE"
    }

    # 3. Bird that should be included (just exactly now)
    live_birds["3"] = {
        "conf": 0.75,
        "box": [50, 50, 60, 60],
        "track_id": 3,
        "last_seen": now,
        "species": "bird",
        "species_label": "AVE"
    }

    response = client.get("/api/birds/live")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    items = data["items"]

    # Only bird 1 and 3 should be in the response
    assert len(items) == 2

    # Verify the correct birds are returned
    bird_uids = [item["bird_uid"] for item in items]
    assert 1 in bird_uids
    assert 3 in bird_uids
    assert 2 not in bird_uids
