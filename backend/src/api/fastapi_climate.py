from fastapi import APIRouter, HTTPException, Depends
import aiohttp
import logging

from src.security.fastapi_auth import get_current_user, UserContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/climate", tags=["Climate"])

@router.get("/location-forecast")
async def get_location_forecast(user: UserContext = Depends(get_current_user)):
    """
    Retorna a localização da granja (baseada no IP) e a previsão do clima atual
    usando a API pública Open-Meteo.
    """
    try:
        async with aiohttp.ClientSession() as session:
            # 1. Obter Localização via IP
            async with session.get("http://ip-api.com/json/") as loc_resp:
                if loc_resp.status != 200:
                    raise HTTPException(status_code=502, detail="Erro ao obter localização")
                loc_data = await loc_resp.json()
                
            lat = loc_data.get("lat", -24.9555)
            lon = loc_data.get("lon", -53.4552)
            city = loc_data.get("city", "Desconhecida")
            region = loc_data.get("regionName", "Desconhecida")
            country = loc_data.get("countryCode", "BR")

            # 2. Obter Previsão do Clima via Open-Meteo (gratuito, sem chave)
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            async with session.get(weather_url) as weather_resp:
                if weather_resp.status != 200:
                    raise HTTPException(status_code=502, detail="Erro ao obter previsão do clima")
                weather_data = await weather_resp.json()
                
            current_weather = weather_data.get("current_weather", {})
            temperature = current_weather.get("temperature", 0.0)
            wind_speed = current_weather.get("windspeed", 0.0)
            
            # Mapeamento simples de condition code (WMO)
            weathercode = current_weather.get("weathercode", 0)
            condition = "Desconhecido"
            if weathercode == 0:
                condition = "Céu limpo"
            elif weathercode in [1, 2, 3]:
                condition = "Parcialmente nublado"
            elif weathercode in [45, 48]:
                condition = "Nevoeiro"
            elif weathercode in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
                condition = "Chuva"
            elif weathercode in [71, 73, 75, 77, 85, 86]:
                condition = "Neve"
            elif weathercode in [95, 96, 99]:
                condition = "Tempestade"

            return {
                "location": {
                    "city": city,
                    "region": region,
                    "country": country,
                    "lat": lat,
                    "lon": lon
                },
                "weather_forecast": {
                    "temperature": temperature,
                    "condition": condition,
                    "wind_speed": wind_speed
                }
            }
    except Exception as e:
        logger.error(f"Erro na rota location-forecast:  {str(e)}")
        # Retorna mock estruturado como fallback de segurança para a FSM
        return {
            "location": {
                "city": "Cascavel",
                "region": "Paraná",
                "country": "BR",
                "lat": -24.9555,
                "lon": -53.4552
            },
            "weather_forecast": {
                "temperature": 25.5,
                "condition": "Ensolarado (Fallback)",
                "wind_speed": 15.0
            }
        }
