import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import sys
import os

# Ensure modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock cv2 before anything else
sys.modules["cv2"] = MagicMock()

# Mock supabase_client
import src.security.fastapi_auth as fastapi_auth
fastapi_auth.supabase_client = MagicMock()

from src.api.fastapi_accounts import router
from src.security.fastapi_auth import get_current_user, UserContext
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)

def override_get_current_user():
    return UserContext(user_id="test", role="admin", tenant_id=1)

app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

def test_accounts_users():
    mock_execute = MagicMock()
    mock_execute.return_value.data = [{"id": "1", "name": "User 1"}]
    fastapi_auth.supabase_client.table.return_value.select.return_value.execute = mock_execute

    response = client.get("/api/accounts/users")
    assert response.status_code == 200
    assert response.json() == {"count": 1, "items": [{"id": "1", "name": "User 1"}]}
