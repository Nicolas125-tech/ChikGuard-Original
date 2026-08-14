import os
import sys
import numpy as np
import pytest

# Define variáveis de ambiente necessárias para testes unitários isolados
os.environ.setdefault("SUPABASE_JWT_SECRET", "test_jwt_secret_key_for_unit_testing_32bytes")
os.environ.setdefault("ENABLE_SAHI", "false")

# Adiciona o diretório backend ao sys.path para importação limpa dos módulos
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir in sys.path:
    sys.path.remove(backend_dir)
sys.path.insert(0, backend_dir)

print("DEBUG: sys.path =", sys.path)
print("DEBUG: plugins in sys.modules =", "plugins" in sys.modules)
if "plugins" in sys.modules:
    print("DEBUG: plugins file =", sys.modules["plugins"].__file__)

# Forçamos a remoção de "plugins" do sys.modules se apontar para src
if "plugins" in sys.modules and "src" in getattr(sys.modules["plugins"], "__file__", ""):
    print("DEBUG: Evicting conflicting plugins module from sys.modules")
    del sys.modules["plugins"]

from src.core.state import (
    sensor_state, live_birds, species_counts, weight_state,
    behavior_state, immobility_state, carcass_state, tamper_state
)
from src.vision.lameness_detector import LamenessDetector
from src.vision.gait_analyzer import GaitAnalyzer
from src.cv_master.behavior_engine import BehaviorEngine
from plugins.biosafety_audit.plugin import BiosafetyAuditPlugin


def test_cv_state_structures():
    """Valida se os dicionários de estado de visão computacional contêm as chaves exigidas pelas regras de negócio."""
    assert isinstance(behavior_state, dict)
    assert "status" in behavior_state
    assert "dispersion_ratio" in behavior_state
    assert "edge_ratio" in behavior_state

    assert isinstance(carcass_state, dict)
    assert "count" in carcass_state
    assert "items" in carcass_state

    assert isinstance(tamper_state, dict)
    assert "alerts_count" in tamper_state


def test_hock_angle_calculation():
    """Testa o cálculo geométrico do ângulo tibiotársico (Hock Angle)."""
    detector = LamenessDetector.__new__(LamenessDetector)  # Sem carregar pesos pesados no teste de geometria
    
    # Triângulo retângulo (90 graus)
    p1 = np.array([0.0, 1.0])  # Quadril (acima)
    p2 = np.array([0.0, 0.0])  # Jarrete (origem)
    p3 = np.array([1.0, 0.0])  # Pata (à direita)
    
    angle = detector.calculate_hock_angle(p1, p2, p3)
    assert abs(angle - 90.0) < 1e-3

    # Ângulo agudo (45 graus)
    p1 = np.array([1.0, 1.0])
    p2 = np.array([0.0, 0.0])
    p3 = np.array([1.0, 0.0])
    angle_45 = detector.calculate_hock_angle(p1, p2, p3)
    assert abs(angle_45 - 45.0) < 1e-3


def test_gait_asymmetry_analysis():
    """Testa o cálculo de assimetria de marcha no GaitAnalyzer."""
    analyzer = GaitAnalyzer(history_len=15)
    
    mock_keypoints_normal = []
    for _ in range(11):
        # [x, y, conf]
        kp = [[0.5, 0.5, 0.9]] * 11
        kp[6] = [0.5, 0.2, 0.9]   # HIP
        kp[9] = [0.4, 0.8, 0.9]   # LEFT_FOOT
        kp[10] = [0.6, 0.8, 0.9]  # RIGHT_FOOT
        mock_keypoints_normal.append(kp)
        
    for kp in mock_keypoints_normal:
        res = analyzer.update_track(1, kp)
        
    assert "mobility_status" in res
    assert bool(res.get("claudication_detected")) is False


def test_biosafety_plugin_overlap_check():
    """Valida a detecção de sobreposição de EPIs com a pessoa no BiosafetyAuditPlugin."""
    plugin = BiosafetyAuditPlugin()
    
    person_box = np.array([100, 100, 300, 500])
    helmet_box_valid = np.array([150, 105, 250, 180])
    helmet_box_outside = np.array([500, 500, 550, 550])
    
    assert bool(plugin._check_overlap(helmet_box_valid, person_box)) is True
    assert bool(plugin._check_overlap(helmet_box_outside, person_box)) is False


def test_behavior_engine_immobility_alert():
    """Testa a geração de alertas de imobilidade pelo BehaviorEngine."""
    engine = BehaviorEngine(immobility_threshold=5.0, immobility_time_sec=0.1)
    
    class MockDetection:
        def __init__(self, tracker_id, xyxy):
            self.tracker_id = tracker_id
            self.xyxy = xyxy

        def __len__(self):
            return len(self.tracker_id)

    dets = MockDetection(tracker_id=[101], xyxy=[np.array([100, 100, 150, 150])])
    
    alerts = engine.update_immobility_and_get_alerts(dets)
    assert len(alerts) == 0
    
    import time
    time.sleep(0.15)
    
    alerts_after = engine.update_immobility_and_get_alerts(dets)
    assert len(alerts_after) >= 1
    assert "101" in alerts_after[0]
