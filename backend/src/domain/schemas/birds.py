from pydantic import BaseModel
from typing import List, Dict, Any

class BirdLiveItem(BaseModel):
    bird_uid: int
    confidence: float
    bbox: List[int]
    track_id: int
    last_seen_seconds: float
    species: str
    species_label: str

class BirdsLiveResponse(BaseModel):
    count: int
    ttl_seconds: float
    items: List[BirdLiveItem]
    species_counts: Dict[str, int]

class WeightLiveResponse(BaseModel):
    camera_id: str
    avg_weight_g: float
    ideal_weight_g: float
    count: int
    confidence: float
    updated_at_epoch: float
