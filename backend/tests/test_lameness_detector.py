import os
import sys
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

# Ajusta sys.path para enxergar src/ e o backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from src.vision.lameness_detector import LamenessDetector

@pytest.fixture
def mock_yolo():
    with patch("ultralytics.YOLO") as mock:
        yield mock

def test_calculate_hock_angle(mock_yolo):
    detector = LamenessDetector(model_path="dummy.pt")
    
    # 90 graus
    p1 = np.array([0.0, 1.0])
    p2 = np.array([0.0, 0.0])
    p3 = np.array([1.0, 0.0])
    angle = detector.calculate_hock_angle(p1, p2, p3)
    assert np.isclose(angle, 90.0)

    # 180 graus
    p1 = np.array([0.0, 1.0])
    p2 = np.array([0.0, 0.0])
    p3 = np.array([0.0, -1.0])
    angle = detector.calculate_hock_angle(p1, p2, p3)
    assert np.isclose(angle, 180.0)

    # 45 graus
    p1 = np.array([1.0, 0.0])
    p2 = np.array([0.0, 0.0])
    p3 = np.array([1.0, 1.0])
    angle = detector.calculate_hock_angle(p1, p2, p3)
    assert np.isclose(angle, 45.0)

    # Divisão por zero (norma zero)
    p1 = np.array([0.0, 0.0])
    p2 = np.array([0.0, 0.0])
    p3 = np.array([1.0, 1.0])
    angle = detector.calculate_hock_angle(p1, p2, p3)
    assert angle == 0.0

def test_analyze_gait_insufficient_history(mock_yolo):
    detector = LamenessDetector(model_path="dummy.pt", history_size=45)
    track_id = 1
    
    # Histórico vazio ou pequeno (< 15 keypoints válidos)
    detector.track_history[track_id] = []
    is_lame, conf_score, details = detector.analyze_gait(track_id)
    assert is_lame is False
    assert conf_score == 0.0

def test_analyze_gait_lame_detected(mock_yolo):
    detector = LamenessDetector(model_path="dummy.pt", history_size=45)
    track_id = 1
    
    # Adicionamos keypoints fictícios válidos no histórico para passar no check i[0] > 0
    # HIP=2, HOCK=3, FOOT=5
    kp = np.zeros((6, 3))
    kp[2] = [0.1, 0.1, 0.9] # HIP
    kp[3] = [0.2, 0.2, 0.9] # HOCK
    kp[5] = [0.3, 0.3, 0.9] # FOOT
    
    detector.track_history[track_id] = [kp] * 20
    
    # Simulamos ângulos com média < 60 e variância < 5.0
    # Ângulos oscilando em torno de 50.0 graus com variância pequena
    angles = [50.0, 51.0, 49.0, 50.0, 51.0, 49.0, 50.0, 51.0, 49.0, 50.0,
              51.0, 49.0, 50.0, 51.0, 49.0, 50.0, 51.0, 49.0, 50.0, 51.0]
    
    with patch.object(detector, 'calculate_hock_angle', side_effect=angles):
        is_lame, conf, details = detector.analyze_gait(track_id)
        
    assert is_lame is True
    assert details["avg_hock_angle"] == pytest.approx(np.mean(angles), 0.01)
    assert details["angle_variance"] == pytest.approx(np.var(angles), 0.01)
    assert details["angle_variance"] < 5.0
    assert conf >= 0.5

def test_analyze_gait_normal_average(mock_yolo):
    detector = LamenessDetector(model_path="dummy.pt", history_size=45)
    track_id = 1
    kp = np.zeros((6, 3))
    kp[2] = [0.1, 0.1, 0.9]
    kp[3] = [0.2, 0.2, 0.9]
    kp[5] = [0.3, 0.3, 0.9]
    detector.track_history[track_id] = [kp] * 20
    
    # Ângulo médio = 70.0 (> 60.0), variância = 1.0 (< 5.0)
    # Não deve classificar como claudicação
    angles = [70.0] * 20
    with patch.object(detector, 'calculate_hock_angle', side_effect=angles):
        is_lame, conf, details = detector.analyze_gait(track_id)
        
    assert is_lame is False

def test_analyze_gait_high_variance(mock_yolo):
    detector = LamenessDetector(model_path="dummy.pt", history_size=45)
    track_id = 1
    kp = np.zeros((6, 3))
    kp[2] = [0.1, 0.1, 0.9]
    kp[3] = [0.2, 0.2, 0.9]
    kp[5] = [0.3, 0.3, 0.9]
    detector.track_history[track_id] = [kp] * 20
    
    # Ângulo médio = 50.0 (< 60.0), mas variância = 16.0 (> 5.0)
    # Não deve classificar como claudicação
    angles = [46.0, 54.0] * 10
    with patch.object(detector, 'calculate_hock_angle', side_effect=angles):
        is_lame, conf, details = detector.analyze_gait(track_id)
        
    assert is_lame is False
