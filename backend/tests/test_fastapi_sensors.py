import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import pytest
from fastapi.testclient import TestClient
import unittest.mock as mock
import sys

# Mock cv2 before importing main
sys.modules["cv2"] = mock.MagicMock()

from src.infrastructure.db.session import engine as session_engine, SessionLocal
from main import fastapi_app
from src.security.fastapi_auth import get_current_user, UserContext

def override_get_current_user():
    return UserContext(user_id="test", role="admin", tenant_id=1)

fastapi_app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(fastapi_app)

from database import db
from flask import Flask

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
db.init_app(app)

with app.app_context():
    db.create_all()

import src.infrastructure.db.session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

shared_engine = create_engine("sqlite:///file:memdb2?mode=memory&cache=shared", connect_args={"check_same_thread": False})
shared_session = sessionmaker(autocommit=False, autoflush=False, bind=shared_engine)

src.db.session.engine = shared_engine
src.db.session.SessionLocal = shared_session

import database
database.db.metadata.create_all(shared_engine)

def override_get_db():
    db = shared_session()
    try:
        yield db
    finally:
        db.close()

from src.infrastructure.db.session import get_db
fastapi_app.dependency_overrides[get_db] = override_get_db

def test_sensors_live():
    response = client.get("/api/sensors/live")
    assert response.status_code == 200
    assert "temperature_c" in response.json()

def test_sensors_ingest():
    payload = {
        "temperature_c": 25.5,
        "humidity_pct": 60.0,
        "ammonia_ppm": 10.0,
        "feed_level_pct": 80.0,
        "water_level_pct": 80.0,
        "source": "test_sensor"
    }
    response = client.post("/api/sensors/ingest", json=payload)
    assert response.status_code == 200

    db_test = shared_session()
    from database import SensorReading, SyncQueueItem
    reading = db_test.query(SensorReading).filter_by(source="test_sensor").first()
    assert reading is not None
    assert reading.temperature_c == 25.5

    sync_item = db_test.query(SyncQueueItem).filter_by(item_type="sensor_reading").first()
    assert sync_item is not None

    db_test.close()
