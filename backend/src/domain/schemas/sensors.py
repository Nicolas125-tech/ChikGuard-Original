from pydantic import BaseModel, Field
from typing import Optional

class SensorIngest(BaseModel):
    temperature_c: float = Field(..., description="Temperatura em Celsius")
    humidity_pct: float = Field(..., description="Umidade relativa (%)")
    ammonia_ppm: float = Field(..., description="Concentracao de Amonia em PPM")
    feed_level_pct: float = Field(..., description="Nivel de racao (%)")
    water_level_pct: float = Field(..., description="Nivel de agua (%)")
    source: Optional[str] = Field("external", description="Origem dos dados")

class SensorLiveResponse(BaseModel):
    camera_id: str
    temperature_c: float
    humidity_pct: float
    ammonia_ppm: float
    feed_level_pct: float
    water_level_pct: float
    source: str
    updated_at_epoch: float
    thresholds: dict
