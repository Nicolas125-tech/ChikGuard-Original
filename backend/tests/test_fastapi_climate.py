import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_location_forecast_success():
    with patch("src.api.fastapi_climate.aiohttp.ClientSession") as mock_session_cls:

        mock_loc_resp = AsyncMock()
        mock_loc_resp.status = 200
        mock_loc_resp.json.return_value = {
            "latitude": -24.9555,
            "longitude": -53.4552,
            "cityName": "Cascavel",
            "regionName": "Parana",
            "countryCode": "BR"
        }

        mock_weather_resp = AsyncMock()
        mock_weather_resp.status = 200
        mock_weather_resp.json.return_value = {
            "current_weather": {
                "temperature": 25.5,
                "windspeed": 10.0,
                "weathercode": 0
            }
        }

        class AsyncContextManagerMock:
            def __init__(self, return_value):
                self.return_value = return_value
            async def __aenter__(self):
                return self.return_value
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_session = AsyncMock()

        def mock_get(url):
            if "geo.json" in url or "ip-api" in url or "ipwho" in url or "freeipapi" in url:
                return AsyncContextManagerMock(mock_loc_resp)
            elif "open-meteo" in url:
                return AsyncContextManagerMock(mock_weather_resp)

        mock_session.get.side_effect = mock_get

        mock_session_cls.return_value = AsyncContextManagerMock(mock_session)

        from src.presentation.api.fastapi_climate import get_location_forecast

        user_ctx = MagicMock()

        result = await get_location_forecast(user=user_ctx)

        assert "location" in result
        assert "weather_forecast" in result
        assert result["weather_forecast"]["temperature"] == 25.5
        assert result["location"]["city"] == "Cascavel"
