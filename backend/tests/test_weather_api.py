import pytest
from fastapi.testclient import TestClient

from main import fastapi_app
from src.security.fastapi_auth import get_current_user, UserContext

client = TestClient(fastapi_app)

def override_get_current_user():
    return UserContext(user_id="test-123", role="admin", tenant_id=1)

def test_get_farm_location_and_weather_unauthorized():
    """Testa a rota sem autenticacao para garantir que retorna 401."""
    response = client.get("/api/climate/location-forecast")
    assert response.status_code == 401

def test_get_farm_location_and_weather():
    """Testa a rota de API FastAPI para localizar a granja e retornar a previsão do clima."""
    fastapi_app.dependency_overrides[get_current_user] = override_get_current_user

    # Testando o endpoint
    response = client.get("/api/climate/location-forecast")
    
    # Validações do status
    assert response.status_code == 200
    
    # Validações do payload JSON
    data = response.json()
    assert data is not None
    assert "location" in data
    assert "city" in data["location"]
    assert "weather_forecast" in data
    assert "temperature" in data["weather_forecast"]
    assert "condition" in data["weather_forecast"]

    fastapi_app.dependency_overrides.clear()
