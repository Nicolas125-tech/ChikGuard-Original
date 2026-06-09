from src.plugins.base import PluginBase, PluginInfo
from typing import Dict, Any, List
import os


class WeatherForecastPlugin(PluginBase):
    info = PluginInfo(
        name="weather_forecast",
        version="0.1.0",
        description="Plugin de previsão do tempo local para otimização climática prévia do galpão.",
    )

    def __init__(self):
        # Temperatura externa padrão e previsão simulada
        self.mock_temp_c = 28.0
        self.mock_heatwave = False
        self.mock_cold_snap = False

    def on_startup(self, context: Dict[str, Any]) -> None:
        # Permite configurar via contexto de inicialização (ex: testes)
        if "mock_temp_c" in context:
            self.mock_temp_c = context["mock_temp_c"]
        if "mock_heatwave" in context:
            self.mock_heatwave = context["mock_heatwave"]
        if "mock_cold_snap" in context:
            self.mock_cold_snap = context["mock_cold_snap"]

    def set_mock_conditions(self, temp_c: float, heatwave: bool = False, cold_snap: bool = False):
        """Método helper para simulações e testes."""
        self.mock_temp_c = temp_c
        self.mock_heatwave = heatwave
        self.mock_cold_snap = cold_snap

    def get_current_weather(self) -> Dict[str, Any]:
        """Retorna as condições climáticas externas atuais."""
        return {
            "temperature_c": self.mock_temp_c,
            "heatwave_active": self.mock_heatwave,
            "cold_snap_active": self.mock_cold_snap,
            "timestamp": "now",
        }

    def get_forecast_12h(self) -> List[Dict[str, Any]]:
        """Gera uma previsão horária simplificada para as próximas 12 horas."""
        forecast = []
        base_temp = self.mock_temp_c

        for hour in range(1, 13):
            # Simula oscilação diurna simples (eleva à tarde, cai à noite)
            temp_offset = 2.0 if hour < 6 else -3.0
            if self.mock_heatwave:
                temp_offset += 5.0
            elif self.mock_cold_snap:
                temp_offset -= 6.0

            forecast.append(
                {
                    "hour_offset": hour,
                    "temp_c": round(base_temp + temp_offset, 1),
                    "humidity_pct": 50 if not self.mock_cold_snap else 80,
                }
            )
        return forecast

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "current_external_temp": self.mock_temp_c,
            "heatwave": self.mock_heatwave,
            "cold_snap": self.mock_cold_snap,
        }


def register():
    return WeatherForecastPlugin()
