import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import json
import os

os.environ["ADMIN_PASSWORD"] = "testpassword"
os.environ["ADMIN_EMAIL"] = "test@example.com"
os.environ["FLASK_ENV"] = "testing"
os.environ["SUPABASE_JWT_SECRET"] = os.environ.get("SUPABASE_JWT_SECRET", "dummy_secret_dummy_secret_dummy_secret_for_tests_32bytes")
os.environ["JWT_SECRET_KEY"] = "testsecret"
os.environ["CORS_ALLOWED_ORIGINS"] = "*"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from src.core.sensors_utils import _safe_json

def test_safe_json_happy_path():
    data = {"key": "value", "number": 123}
    result = _safe_json(data)
    assert result == json.dumps(data, ensure_ascii=False)


def test_safe_json_error_path():
    # A complex number is not JSON serializable
    data = {"key": 1 + 2j}
    result = _safe_json(data)
    # The actual implementation of _safe_json returns "{}" on failure
    assert result == "{}"
