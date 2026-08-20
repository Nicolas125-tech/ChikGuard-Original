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

from src.vision.radial_light_corrector import RadialBrooderLightCorrector
from src.vision.tri_zone_analyzer import TriZoneBehaviorAnalyzer


def test_radial_brooder_light_corrector():
    """
    Valida a atenuação gradual de brilho da luz da campânula (Equações 1-4 de Saltoratto et al., 2013).
    """
    corrector = RadialBrooderLightCorrector(center_xy=(320, 240), r_min=50.0, r_max=200.0, max_attenuation=0.40)

    # 1. Cria frame superbrilhante no centro (simulando lâmpada de aquecimento ligada)
    bright_frame = np.full((480, 640, 3), 250, dtype=np.uint8)

    corrected = corrector.correct_intensity(bright_frame)

    assert corrected.shape == (480, 640, 3)
    # No centro da luz (320, 240), a intensidade deve cair aproximadamente 40% (250 * 0.6 = 150)
    center_val = float(corrected[240, 320, 0])
    assert center_val < 200.0

    # Na borda externa (fora de r_max = 200), a iluminação original deve ser preservada (250)
    edge_val = float(corrected[10, 10, 0])
    assert edge_val == 250.0


def test_tri_zone_behavior_analyzer():
    """
    Valida o zonamento trifásico (Bebedouro, Aquecimento, Comedouro) e diagnóstico de bem-estar animal.
    """
    analyzer = TriZoneBehaviorAnalyzer(window_size=100)

    # 1. Teste de Distribuição Equilibrada (Conforto Térmico)
    # Frame 640x480: Bebedouro (x < 211), Aquecimento (211 <= x < 422), Comedouro (x >= 422)
    centers_balanced = [
        (100.0, 240.0),  # Bebedouro
        (300.0, 240.0),  # Aquecimento
        (500.0, 240.0),  # Comedouro
    ]
    res_balanced = analyzer.analyze_zones(centers_balanced, frame_width=640, frame_height=480)

    assert res_balanced["drinker_count"] == 1
    assert res_balanced["brooder_count"] == 1
    assert res_balanced["feeder_count"] == 1
    assert res_balanced["welfare_status"] == "CONFORTO_IDEAL"
    assert res_balanced["welfare_index"] >= 0.90

    # 2. Teste de Estresse por Frio (Pintainhos aglomerados sob a luz de aquecimento > 60%)
    centers_cold = [
        (300.0, 240.0),
        (320.0, 240.0),
        (350.0, 240.0),
        (380.0, 240.0),
    ]
    res_cold = analyzer.analyze_zones(centers_cold, frame_width=640, frame_height=480)

    assert res_cold["brooder_pct"] == 1.0
    assert res_cold["welfare_status"] == "ESTRESSE_FRIO"

    # 3. Resumo cumulativo de frequências (Figura 22 do artigo)
    summary = analyzer.get_stay_frequency_summary()
    assert summary["total_samples"] == 2
    assert summary["sum_brooder"] == 5
    assert summary["sum_drinker"] == 1
    assert summary["sum_feeder"] == 1
