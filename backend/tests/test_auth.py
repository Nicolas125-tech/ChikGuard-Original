import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import os
import pytest
from unittest.mock import patch, MagicMock
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

@patch("src.api.auth.create_client")
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
