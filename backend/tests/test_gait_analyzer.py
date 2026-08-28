import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import os
import sys
from datetime import datetime, timedelta

from src.domain.vision.gait_analyzer import GaitAnalyzer

# Ajusta sys.path para enxergar src/ e o backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


def _generate_keypoints(hip_x, hip_y, lfoot_y, rfoot_y):
    """Gera um esqueleto simplificado de ave com coordenadas de teste."""
    # Retorna 11 keypoints [[x, y, conf], ...]
    return [
        [hip_x, hip_y - 20, 0.9],  # Beak
        [hip_x - 2, hip_y - 22, 0.8],  # Eye L
        [hip_x + 2, hip_y - 22, 0.8],  # Eye R
        [hip_x, hip_y - 10, 0.9],  # Neck
        [hip_x - 15, hip_y - 5, 0.7],  # Wing L
        [hip_x + 15, hip_y - 5, 0.7],  # Wing R
        [hip_x, hip_y, 0.9],  # Hip
        [hip_x - 8, hip_y + 10, 0.9],  # Knee L
        [hip_x + 8, hip_y + 10, 0.9],  # Knee R
        [hip_x - 10, lfoot_y, 0.9],  # Foot L
        [hip_x + 10, rfoot_y, 0.9],  # Foot R
    ]


def test_gait_analyzer_calibrating():
    """Valida que o analisador aguarda frames suficientes antes de emitir diagnóstico."""
    analyzer = GaitAnalyzer()

    # 5 frames de atualização
    for i in range(5):
        kps = _generate_keypoints(100 + i * 5, 100, 120, 120)
        res = analyzer.update_track(track_id=1, keypoints=kps)

    assert res["status"] == "CALIBRATING"


def test_gait_analyzer_normal_walking():
    """Valida a análise de uma ave caminhando normalmente com passos simétricos."""
    analyzer = GaitAnalyzer(history_len=20)
    base_time = datetime.utcnow()

    # Simula 15 frames de caminhada simétrica e saudável
    for i in range(15):
        # A ave se move no eixo X
        x = 100 + i * 10
        # Simula oscilação vertical das patas alternadamente (passos)
        left_foot_y = 120 + (10 if i % 2 == 0 else 0)
        right_foot_y = 120 + (0 if i % 2 == 0 else 10)

        kps = _generate_keypoints(x, 100, left_foot_y, right_foot_y)
        res = analyzer.update_track(
            track_id=1, keypoints=kps, timestamp=base_time + timedelta(seconds=i * 0.1)
        )

    assert res["status"] == "ANALYZED"
    assert res["mobility_status"] == "NORMAL"
    assert bool(res["claudication_detected"]) is False
    assert bool(res["is_lethargic"]) is False
    assert res["gait_score"] < 0.25


def test_gait_analyzer_claudication():
    """Valida a detecção de claudicação quando há assimetria acentuada de extensão das patas."""
    analyzer = GaitAnalyzer(history_len=20)
    base_time = datetime.utcnow()

    # Simula 15 frames onde a perna esquerda estica muito mais que a direita (ave mancando)
    for i in range(15):
        x = 100 + i * 5
        left_foot_y = 135  # Extensão grande (membro saudável)
        right_foot_y = 105  # Extensão muito curta (membro lesionado/encolhido)

        kps = _generate_keypoints(x, 100, left_foot_y, right_foot_y)
        res = analyzer.update_track(
            track_id=2, keypoints=kps, timestamp=base_time + timedelta(seconds=i * 0.1)
        )

    assert res["status"] == "ANALYZED"
    assert res["mobility_status"] == "CLAUDICACAO_DETECTADA"
    assert bool(res["claudication_detected"]) is True
    assert res["gait_score"] >= 0.25


def test_gait_analyzer_lethargy():
    """Valida a detecção de letargia quando a ave permanece estática por muito tempo."""
    analyzer = GaitAnalyzer(history_len=20)
    base_time = datetime.utcnow()

    # Simula 15 frames sem deslocamento de quadril (ave apática) com delta > 1.5s
    for i in range(15):
        kps = _generate_keypoints(100, 100, 120, 120)
        res = analyzer.update_track(
            track_id=3, keypoints=kps, timestamp=base_time + timedelta(seconds=i * 0.15)
        )

    assert res["status"] == "ANALYZED"
    assert res["mobility_status"] == "LETARGIA_APATIA"
    assert bool(res["is_lethargic"]) is True
    assert bool(res["claudication_detected"]) is False
