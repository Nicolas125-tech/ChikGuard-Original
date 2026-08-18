import os
import sys
import numpy as np
import pytest

os.environ.setdefault("SUPABASE_JWT_SECRET", "test_jwt_secret_key_for_unit_testing_32bytes")
os.environ.setdefault("ENABLE_SAHI", "false")

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from src.vision.tamper_detector import CameraTamperDetector
from src.vision.spatial_heatmap import SpatialHeatmapAccumulator
from src.vision.weight_estimator import BiometricWeightEstimator


def test_tamper_detector_dark_and_blur():
    """Valida a detecção de oclusão (escuridão) e desfoque no CameraTamperDetector."""
    detector = CameraTamperDetector(min_brightness=15.0, min_laplacian_var=80.0)
    
    # 1. Frame totalmente preto (lente coberta)
    black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    res_black = detector.analyze_frame(black_frame)
    
    assert res_black["is_dark"] is True
    assert res_black["is_blurred"] is True
    assert "DARK_OR_COVERED" in res_black["causes"]

    # 2. Frame normal com brilho suficiente e textura
    frame_bright = np.zeros((480, 640), dtype=np.uint8)
    import cv2
    frame_bright[::2, ::2] = 255
    frame_bright[1::2, 1::2] = 255
    frame_bright[:240, :] = 180
    frame_bright[:240, :] = 180  # garante brilho médio > 15
    
    res_sharp = detector.analyze_frame(frame_bright)
    assert res_sharp["is_dark"] is False
    assert res_sharp["is_blurred"] is False


def test_spatial_heatmap_accumulator():
    """Valida o acúmulo de posições de centroides de aves no SpatialHeatmapAccumulator."""
    accumulator = SpatialHeatmapAccumulator(default_grid_size=20, history_decay_sec=3600.0)
    
    # Adiciona 5 aves no centro do frame (320, 240) em frame 640x480
    centers = [(320.0, 240.0)] * 5
    accumulator.add_detections(centers, frame_width=640, frame_height=480)
    
    matrix = accumulator.get_grid_matrix(grid_size=20)
    assert matrix.shape == (20, 20)
    
    # A célula central da grade 20x20 para ponto 0.5 é (linha 9, coluna 9)
    assert matrix[9, 9] == 1.0
    
    pts_3d = accumulator.get_3d_points(grid_size=20)
    assert len(pts_3d) >= 1
    assert any(pt["x"] == 9 and pt["y"] == 9 for pt in pts_3d)


def test_biometric_weight_estimator():
    """Valida a estimativa de peso individual e do lote no BiometricWeightEstimator."""
    estimator = BiometricWeightEstimator()
    
    frame_shape = (480, 640, 3)
    # Bounding box típica de pintinho (40x40 px)
    box_chick = [100, 100, 140, 140]
    res_chick = estimator.estimate_bird_weight(box_chick, frame_shape, species="chick", batch_age_days=7)
    
    assert 35.0 <= res_chick["weight_g"] <= 400.0

    # Teste de lote
    detections = [
        {"class_id": 14, "species": "chick", "box": [100, 100, 140, 140]},
        {"class_id": 14, "species": "chick", "box": [200, 200, 250, 250]},
    ]
    flock_res = estimator.estimate_flock_weight(detections, frame_shape, batch_age_days=14)
    
    assert flock_res["count"] == 2
    assert flock_res["avg_weight_g"] > 0
