import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import os
import sys
import numpy as np
import pytest

os.environ.setdefault("SUPABASE_JWT_SECRET", "test_jwt_secret_key_for_unit_testing_32bytes")
os.environ.setdefault("ENABLE_SAHI", "false")

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from src.vision.background_subtractor_paper import PaperBackgroundSubtractor
from src.vision.zone_time_series import ZoneTimeSeriesTracker


def test_paper_background_subtractor_and_floodfill():
    """
    Valida a subtração de fundo, o Fecho morfológico e a contagem por Inundação (Flood Fill)
    (Saltoratto et al., 2013, Seção 3.1, Equações 5 a 9).
    """
    subtractor = PaperBackgroundSubtractor(threshold_val=150)

    # 1. Imagem de fundo limpa da baia (sem aves)
    bg_frame = np.full((480, 640, 3), 200, dtype=np.uint8)
    subtractor.set_background(bg_frame)

    # 2. Imagem atual com 2 manchas escuras (simulando 2 pintainhos)
    curr_frame = bg_frame.copy()
    curr_frame[100:140, 100:140] = 30  # Pintainho 1
    curr_frame[200:250, 300:350] = 30  # Pintainho 2

    res = subtractor.process_frame(curr_frame)

    assert res["blobs_count"] >= 2
    assert res["total_mask_area"] > 0
    assert len(res["blobs_centers"]) >= 2


def test_zone_time_series_tracker():
    """
    Valida o registrador de Séries Temporais F_stay(t) = (t, N_bebedouro, N_luz, N_comedouro)
    e os somatórios cumulativos das Figuras 20 a 22 do artigo científico.
    """
    tracker = ZoneTimeSeriesTracker(max_history_len=100)

    # Simula 5 amostras temporais
    tracker.record_sample(drinker_count=2, brooder_count=5, feeder_count=3, timestamp=1000.0)
    tracker.record_sample(drinker_count=1, brooder_count=6, feeder_count=2, timestamp=1005.0)

    series = tracker.get_time_series(limit=10)
    assert len(series) == 2
    assert series[0]["drinker"] == 2
    assert series[0]["brooder"] == 5

    summary = tracker.get_cumulative_summary()
    assert summary["total_samples"] == 2
    assert summary["cumulative_drinker"] == 3
    assert summary["cumulative_brooder"] == 11
    assert summary["cumulative_feeder"] == 5
    assert summary["most_frequented_zone"] == "AQUECIMENTO"
