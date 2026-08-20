import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
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

def test_live_birds_empty_state():
    """
    Test that an empty state returns an empty list and count of 0.
    """
    live_birds.clear()

    response = client.get("/api/birds/live")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert data["count"] == 0
    assert len(data["items"]) == 0


def test_live_birds_formatting_and_sorting():
    """
    Test data formatting, rounding, sorting and default values handling.
    """
    from src.core.state import species_counts
    now = time.time()

    live_birds.clear()
    species_counts.clear()
    species_counts["bird"] = 2

    # 1. Missing optional fields to test defaults
    live_birds["2"] = {
        "conf": 0.88888,
        "box": [10, 20, 30, 40],
        "last_seen": now - 1.5,
    }

    # 2. All fields present
    live_birds["1"] = {
        "conf": 0.99999,
        "box": [0, 0, 10, 10],
        "track_id": 5,
        "last_seen": now - 0.5,
        "species": "chicken",
        "species_label": "GAL"
    }

    response = client.get("/api/birds/live")
    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 2
    assert data["species_counts"] == {"bird": 2}

    items = data["items"]

    # Should be sorted by bird_uid, so 1 then 2
    assert items[0]["bird_uid"] == 1
    assert items[0]["confidence"] == 1.0  # round(0.99999, 4)
    assert items[0]["track_id"] == 5
    assert items[0]["species"] == "chicken"
    assert items[0]["species_label"] == "GAL"

    assert items[1]["bird_uid"] == 2
    assert items[1]["confidence"] == 0.8889  # round(0.88888, 4)
    assert items[1]["track_id"] == -1 # default
    assert items[1]["species"] == "bird" # default
    assert items[1]["species_label"] == "AVE" # default
    assert items[1]["bbox"] == [10, 20, 30, 40]
