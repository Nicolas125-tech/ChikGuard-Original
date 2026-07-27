import os
import pytest
from src.core.config import Settings

def test_config_jwt_secret_fallback_production(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="JWT_SECRET_KEY environment variable MUST be set in production"):
        Settings()

def test_config_jwt_secret_fallback_development(monkeypatch):
    monkeypatch.setenv("ENV", "development")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    settings = Settings()
    assert settings.jwt_secret_key == "dev-secret-key-change-in-production-long-enough"

def test_config_jwt_secret_set(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "mysecretkey")
    settings = Settings()
    assert settings.jwt_secret_key == "mysecretkey"
