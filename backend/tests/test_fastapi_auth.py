import os
os.environ["SUPABASE_JWT_SECRET"] = "dummy_secret_for_tests"

import pytest
import jwt
from unittest.mock import patch, MagicMock
import sys

# Ensure modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock cv2 before anything else
sys.modules["cv2"] = MagicMock()

from src.security.fastapi_auth import get_current_user
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_get_current_user_expired_token():
    with patch("src.security.fastapi_auth.jwt.get_unverified_header") as mock_header:
        mock_header.return_value = {"alg": "HS256"}
        with patch("src.security.fastapi_auth.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError("Signature has expired")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token="fake_expired_token")

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Token expired"

@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    with patch("src.security.fastapi_auth.jwt.get_unverified_header") as mock_header:
        mock_header.return_value = {"alg": "HS256"}
        with patch("src.security.fastapi_auth.jwt.decode") as mock_decode:
            mock_decode.side_effect = jwt.DecodeError("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token="fake_invalid_token")

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Erro de processamento de token"

@pytest.mark.asyncio
async def test_get_current_user_missing_sub():
    with patch("src.security.fastapi_auth.jwt.get_unverified_header") as mock_header:
        mock_header.return_value = {"alg": "HS256"}
        with patch("src.security.fastapi_auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {"role": "admin"} # Missing 'sub'

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token="fake_token_no_sub")

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Invalid token payload"

@pytest.mark.asyncio
async def test_get_current_user_no_decoded_payload():
    with patch("src.security.fastapi_auth.jwt.get_unverified_header") as mock_header:
        mock_header.return_value = {"alg": "HS256"}
        with patch("src.security.fastapi_auth.jwt.decode") as mock_decode:
            # We want to simulate the case where `decoded` remains None but no exception is thrown
            mock_decode.return_value = None

            with patch("src.security.fastapi_auth.SUPABASE_JWT_SECRET", ""):
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(token="fake_token")

                assert exc_info.value.status_code == 401
                assert exc_info.value.detail == "Não foi possível validar o token"

@pytest.mark.asyncio
async def test_get_current_user_no_token():
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token="")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid token"
