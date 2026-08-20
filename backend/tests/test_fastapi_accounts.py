import os
os.environ["SUPABASE_JWT_SECRET"] = os.environ.get("SUPABASE_JWT_SECRET", "dummy_secret_dummy_secret_dummy_secret_for_tests_32bytes")

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys

# Ensure modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock cv2 before anything else

from src.api.fastapi_accounts import router
from src.security.fastapi_auth import get_current_user, UserContext
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)

def override_get_current_user():
    return UserContext(user_id="test", role="admin", tenant_id=1)

app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

@patch("src.api.fastapi_accounts.supabase_client")
def test_accounts_users(mock_supabase):
    mock_execute = MagicMock()
    mock_execute.execute.return_value.data = [{"id": "1", "name": "User 1"}]
    mock_supabase.table.return_value.select.return_value = mock_execute

    response = client.get("/api/accounts/users")
    assert response.status_code == 200
    assert response.json() == {"count": 1, "items": [{"id": "1", "name": "User 1"}]}
