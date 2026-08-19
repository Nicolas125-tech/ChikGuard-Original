import pytest
import jwt
from unittest.mock import patch, MagicMock
from src.api.fastapi_ws import connect, disconnect

@pytest.mark.asyncio
async def test_connect_no_token():
    # Test connection without token
    assert await connect("sid_123", {}, None) == False
    assert await connect("sid_123", {}, {}) == False
    assert await connect("sid_123", {}, {"token": ""}) == False

@pytest.mark.asyncio
@patch('src.api.fastapi_ws.jwt.decode')
@patch('src.api.fastapi_ws.jwt.get_unverified_header')
@patch('src.api.fastapi_ws.os.environ.get')
async def test_connect_valid_hs256_token(mock_env_get, mock_get_header, mock_decode):
    # Test valid HS256 token
    mock_env_get.return_value = "valid_secret_key"
    mock_get_header.return_value = {"alg": "HS256"}
    mock_decode.return_value = {"sub": "user_123"}

    with patch('src.api.fastapi_ws.sio.session') as mock_session:
        # Mock async context manager for session
        mock_session_instance = MagicMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        result = await connect("sid_123", {}, {"token": "valid_token"})

        assert result == True
        mock_decode.assert_called_once_with("valid_token", "valid_secret_key", algorithms=["HS256"], audience="authenticated")

@pytest.mark.asyncio
@patch('src.api.fastapi_ws.jwt.decode')
@patch('src.api.fastapi_ws.jwt.get_unverified_header')
@patch('src.api.fastapi_ws._get_supabase_public_key')
async def test_connect_valid_es256_token(mock_get_key, mock_get_header, mock_decode):
    # Test valid ES256 token
    mock_get_header.return_value = {"alg": "ES256"}
    mock_get_key.return_value = "public_key"
    mock_decode.return_value = {"sub": "user_123"}

    with patch('src.api.fastapi_ws.sio.session') as mock_session:
        # Mock async context manager for session
        mock_session_instance = MagicMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        result = await connect("sid_123", {}, {"token": "valid_token"})

        assert result == True
        mock_decode.assert_called_once_with("valid_token", "public_key", algorithms=["ES256"], audience="authenticated")

@pytest.mark.asyncio
@patch('src.api.fastapi_ws.jwt.decode')
@patch('src.api.fastapi_ws.jwt.get_unverified_header')
@patch('src.api.fastapi_ws.os.environ.get')
async def test_connect_missing_secret(mock_env_get, mock_get_header, mock_decode):
    # Test missing JWT secret
    mock_env_get.return_value = None
    mock_get_header.return_value = {"alg": "HS256"}

    with patch('src.api.fastapi_ws.SUPABASE_JWT_SECRET', None):
        result = await connect("sid_123", {}, {"token": "valid_token"})

        assert result == False
        mock_decode.assert_not_called()

@pytest.mark.asyncio
async def test_disconnect():
    # Should not raise any exception
    await disconnect("sid_123")
