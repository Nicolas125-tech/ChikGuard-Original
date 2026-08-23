import pytest
from fastapi.testclient import TestClient
from src.security.fastapi_auth import SUPABASE_JWT_SECRET
from unittest.mock import patch, MagicMock
from main import fastapi_app
import jwt
import os

client = TestClient(fastapi_app)

def test_video_feed_without_token():
    response = client.get("/api/webrtc/video")
    assert response.status_code == 401
    assert "Token JWT requerido" in response.json()["detail"]

@patch("src.api.fastapi_webrtc.get_current_user")
def test_video_feed_with_invalid_token(mock_get_current_user):
    from fastapi import HTTPException
    mock_get_current_user.side_effect = HTTPException(status_code=401, detail="Invalid token payload")

    response = client.get("/api/webrtc/video?token=invalid_token")
    assert response.status_code == 401
    assert "Invalid token payload" in response.json()["detail"]

@patch("src.api.fastapi_webrtc.get_current_user")
@patch("src.api.fastapi_webrtc.get_global_frame")
def test_video_feed_with_valid_token(mock_get_global_frame, mock_get_current_user):
    # Mock authentication success
    mock_get_current_user.return_value = MagicMock(user_id="test_user", role="operator", tenant_id=1)

    # Mock video generator to exit immediately
    import cv2
    import numpy as np
    mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_get_global_frame.return_value = mock_frame

    # Using patch to bypass the infinite stream for testing
    with patch("src.api.fastapi_webrtc.asyncio.sleep", side_effect=GeneratorExit()):
        response = client.get("/api/webrtc/video?token=valid_token")
        assert response.status_code == 200
        assert "multipart/x-mixed-replace" in response.headers["content-type"]
