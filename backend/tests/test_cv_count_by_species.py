import pytest
from src.core.cv_engine import count_by_species

def test_count_by_species_empty():
    res = count_by_species({}, [], 100.0, 10.0)
    assert res == {"chicks": 0, "hens": 0, "total": 0}

def test_count_by_species_mixed_detections():
    live_birds = {}
    detections = [
        {"species": "chick"},
        {"species": "hen"},
        {"species": "chick"},
        {"species": "unknown"},  # Falls back to hen according to logic
        {}, # default is "bird", which falls back to hen
    ]
    res = count_by_species(live_birds, detections, 100.0, 10.0)
    assert res["chicks"] == 2
    assert res["hens"] == 3

def test_count_by_species_live_birds():
    # Only those updated within TTL should count in 'total'
    now = 100.0
    bird_live_ttl = 10.0
    live_birds = {
        "bird1": {"last_seen": 95.0}, # active
        "bird2": {"last_seen": 85.0}, # stale
        "bird3": {"last_seen": 99.0}, # active
    }
    detections = []
    res = count_by_species(live_birds, detections, now, bird_live_ttl)
    assert res["total"] == 2

def test_count_by_species_combined():
    now = 100.0
    bird_live_ttl = 10.0
    live_birds = {
        "bird1": {"last_seen": 95.0},
        "bird2": {"last_seen": 100.0},
    }
    detections = [
        {"species": "hen"},
    ]
    res = count_by_species(live_birds, detections, now, bird_live_ttl)
    assert res["chicks"] == 0
    assert res["hens"] == 1
    assert res["total"] == 2
