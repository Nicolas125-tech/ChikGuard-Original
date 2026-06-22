import pytest
from fastapi.testclient import TestClient

from main import fastapi_app

client = TestClient(fastapi_app)

def test_get_farm_location_and_weather():
    """Testa a rota de API FastAPI para localizar a granja e retornar a previsão do clima."""
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
