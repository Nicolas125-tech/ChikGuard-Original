import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import pytest
from src.vision.zone_time_series import ZoneTimeSeriesTracker

def test_empty_summary():
    tracker = ZoneTimeSeriesTracker()
    summary = tracker.get_cumulative_summary()
    assert summary["total_samples"] == 0
    assert summary["cumulative_drinker"] == 0
    assert summary["cumulative_brooder"] == 0
    assert summary["cumulative_feeder"] == 0
    assert summary["most_frequented_zone"] == "NENHUMA"

def test_zero_counts():
    tracker = ZoneTimeSeriesTracker()
    tracker.record_sample(0, 0, 0)
    tracker.record_sample(0, 0, 0)
    summary = tracker.get_cumulative_summary()
    assert summary["total_samples"] == 2
    assert summary["cumulative_drinker"] == 0
    assert summary["cumulative_brooder"] == 0
    assert summary["cumulative_feeder"] == 0
    assert summary["most_frequented_zone"] == "BEBEDOURO"  # or first key

def test_normal_counts():
    tracker = ZoneTimeSeriesTracker()
    tracker.record_sample(5, 10, 2)
    tracker.record_sample(0, 15, 3)
    summary = tracker.get_cumulative_summary()
    assert summary["total_samples"] == 2
    assert summary["cumulative_drinker"] == 5
    assert summary["cumulative_brooder"] == 25
    assert summary["cumulative_feeder"] == 5
    assert summary["most_frequented_zone"] == "AQUECIMENTO"

def test_max_history():
    tracker = ZoneTimeSeriesTracker(max_history_len=2)
    tracker.record_sample(1, 0, 0)
    tracker.record_sample(0, 2, 0)
    tracker.record_sample(0, 0, 3)

    summary = tracker.get_cumulative_summary()
    assert summary["total_samples"] == 2
    assert summary["cumulative_drinker"] == 0
    assert summary["cumulative_brooder"] == 2
    assert summary["cumulative_feeder"] == 3
    assert summary["most_frequented_zone"] == "COMEDOURO"

def test_get_time_series():
    tracker = ZoneTimeSeriesTracker()
    tracker.record_sample(1, 1, 1, timestamp=100.0)
    tracker.record_sample(2, 2, 2, timestamp=200.0)
    series = tracker.get_time_series(limit=1)
    assert len(series) == 1
    assert series[0]["timestamp"] == 200.0
    assert series[0]["total"] == 6
