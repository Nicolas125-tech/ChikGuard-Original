import sys
from unittest.mock import MagicMock

sys.modules["cv2"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["ultralytics"] = MagicMock()
sys.modules["supervision"] = MagicMock()
import os
from unittest.mock import MagicMock, patch

from src.presentation.api.auth import _get_supabase_client


def test_get_supabase_client_missing_url():
    env_mock = {"SUPABASE_SERVICE_ROLE_KEY": "some-key"}
    with patch.dict(os.environ, env_mock, clear=True):
        assert _get_supabase_client() is None

def test_get_supabase_client_missing_key():
    env_mock = {"SUPABASE_URL": "http://some-url"}
    with patch.dict(os.environ, env_mock, clear=True):
        assert _get_supabase_client() is None

def test_get_supabase_client_missing_both():
    env_mock = {}
    with patch.dict(os.environ, env_mock, clear=True):
        assert _get_supabase_client() is None

@patch("src.presentation.api.auth.create_client")
def test_get_supabase_client_success(mock_create_client):
    mock_create_client.return_value = MagicMock()

    env_mock = {
        "SUPABASE_URL": "http://some-url",
        "SUPABASE_SERVICE_ROLE_KEY": "some-key"
    }
    with patch.dict(os.environ, env_mock, clear=True):
        client = _get_supabase_client()
        assert client is not None
        mock_create_client.assert_called_once_with("http://some-url", "some-key")
