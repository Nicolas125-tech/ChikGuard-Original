import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import os
os.environ["SUPABASE_JWT_SECRET"] = os.environ.get("SUPABASE_JWT_SECRET", "dummy_secret_dummy_secret_dummy_secret_for_tests_32bytes")

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys

# Ensure modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock cv2 before anything else
sys.modules["cv2"] = MagicMock()

from src.presentation.api.fastapi_accounts import router
from src.security.fastapi_auth import get_current_user, UserContext
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)

def override_get_current_user():
    return UserContext(user_id="test", role="admin", tenant_id=1)

app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

@patch("src.presentation.api.fastapi_accounts.supabase_client")
def test_accounts_users(mock_supabase):
    mock_execute = MagicMock()
    mock_execute.execute.return_value.data = [{"id": "1", "name": "User 1"}]
    mock_execute.eq.return_value = mock_execute
    mock_supabase.table.return_value.select.return_value = mock_execute

    response = client.get("/api/accounts/users")
    assert response.status_code == 200
    assert response.json() == {"count": 1, "items": [{"id": "1", "name": "User 1"}]}

from src.presentation.api.fastapi_accounts import write_audit_log
import json

@patch("database.AuditLog")
def test_write_audit_log_success(mock_audit_log_class):
    mock_db = MagicMock()
    actor = "admin"
    action = "delete"
    details = {"id": 1}

    write_audit_log(mock_db, actor, action, details)

    mock_audit_log_class.assert_called_once_with(
        actor=actor,
        action=action,
        source="security",
        details_json=json.dumps(details, ensure_ascii=False)
    )

    mock_db.add.assert_called_once_with(mock_audit_log_class.return_value)
    mock_db.commit.assert_called_once()

@patch("database.AuditLog")
@patch("src.presentation.api.fastapi_accounts.logger")
def test_write_audit_log_exception(mock_logger, mock_audit_log_class):
    mock_db = MagicMock()
    mock_db.commit.side_effect = Exception("DB error")

    actor = "admin"
    action = "delete"
    details = {"id": 1}

    write_audit_log(mock_db, actor, action, details)

    mock_logger.error.assert_called_once_with("Failed to write audit log: %s", "DB error")
