from datetime import datetime
from typing import Any, Dict, List, Tuple

import numpy as np


class GaitAnalyzer:
    """
    Analisador de marcha e mobilidade individual de aves a partir de keypoints (YOLOv8-Pose).
    Identifica claudicação (asimetria de passo), apatia e letargia com base na trajetória temporal.
    """

    # Índices dos Keypoints do esqueleto YOLOv8-Pose para aves
    KP_BEAK = 0
    KP_EYE_L = 1
    KP_EYE_R = 2
    KP_NECK = 3
    KP_LEFT_WING = 4
    KP_RIGHT_WING = 5
    KP_HIP = 6
    KP_LEFT_KNEE = 7
    KP_RIGHT_KNEE = 8
    KP_LEFT_FOOT = 9
    KP_RIGHT_FOOT = 10

    def __init__(self, history_len: int = 30, fps: int = 15):
        self.history_len = history_len
        self.fps = fps
        # Histórico estruturado: track_id -> [ {"timestamp": datetime, "keypoints": [[x, y, conf], ...]} ]
        self._history: Dict[int, List[Dict[str, Any]]] = {}

    def update_track(
        self, track_id: int, keypoints: List[List[float]], timestamp: datetime = None
    ) -> Dict[str, Any]:
        """Adiciona uma leitura de keypoints ao histórico do ID rastreado e executa a análise."""
        if timestamp is None:
            timestamp = datetime.utcnow()

        if len(keypoints) < 11:
            return {"status": "INSUFFICIENT_KEYPOINTS"}

        track_buffer = self._history.setdefault(track_id, [])
        track_buffer.append({"timestamp": timestamp, "keypoints": keypoints})

        # Mantém o tamanho do histórico limitado
        if len(track_buffer) > self.history_len:
            track_buffer.pop(0)

        return self._analyze_individual(track_id)

    def remove_track(self, track_id: int):
        """Descarta o histórico de uma ave que saiu do campo de visão da câmera."""
        self._history.pop(track_id, None)

    # ── Funções de Cálculo Biomecânico (SRP - Single Responsibility) ──

    def _extract_positions_by_index(
        self, history: List[Dict[str, Any]], kp_index: int, min_conf: float = 0.4
    ) -> List[np.ndarray]:
        """Extrai as coordenadas (x, y) válidas ao longo do histórico para um determinado keypoint."""
        positions = []
        for frame in history:
            kp = frame["keypoints"][kp_index]
            if kp[2] > min_conf:
                positions.append(np.array([kp[0], kp[1]]))
        return positions

    def _calculate_total_distance(self, positions: List[np.ndarray]) -> float:
        """Calcula o deslocamento euclidiano cumulativo a partir de uma lista de pontos."""
        if len(positions) < 2:
            return 0.0
        diffs = [positions[i] - positions[i - 1] for i in range(1, len(positions))]
        return sum(np.linalg.norm(d) for d in diffs)

    def _calculate_gait_score_and_claudication(
        self, history: List[Dict[str, Any]]
    ) -> Tuple[float, bool]:
        """Calcula a assimetria da amplitude do passo e indica a presença de claudicação."""
        left_extensions = []
        right_extensions = []

        for frame in history:
            kps = frame["keypoints"]
            kp_hip = kps[self.KP_HIP]
            kp_lfoot = kps[self.KP_LEFT_FOOT]
            kp_rfoot = kps[self.KP_RIGHT_FOOT]

            # Confiança mínima recomendada para os três pontos simultaneamente
            if kp_hip[2] > 0.4 and kp_lfoot[2] > 0.4 and kp_rfoot[2] > 0.4:
                hip_pos = np.array([kp_hip[0], kp_hip[1]])
                left_extensions.append(
                    np.linalg.norm(np.array([kp_lfoot[0], kp_lfoot[1]]) - hip_pos)
                )
                right_extensions.append(
                    np.linalg.norm(np.array([kp_rfoot[0], kp_rfoot[1]]) - hip_pos)
                )

        if len(left_extensions) < 5:
            return 0.0, False

        avg_left = sum(left_extensions) / len(left_extensions)
        avg_right = sum(right_extensions) / len(right_extensions)

        if avg_left <= 0 or avg_right <= 0:
            return 0.0, False

        # Razão de assimetria relativa do passo
        asymmetry_ratio = abs(avg_left - avg_right) / max(avg_left, avg_right)
        gait_score = round(asymmetry_ratio, 2)
        claudication_detected = asymmetry_ratio > 0.25  # Mais de 25% de assimetria indica coxeira

        return gait_score, claudication_detected

    def _determine_mobility_status(self, claudication_detected: bool, is_lethargic: bool) -> str:
        """Determina o status clínico simplificado com base nas detecções."""
        if claudication_detected:
            return "CLAUDICACAO_DETECTADA"
        if is_lethargic:
            return "LETARGIA_APATIA"
        return "NORMAL"

    def _analyze_individual(self, track_id: int) -> Dict[str, Any]:
        """Executa a análise biomecânica global para o track do animal."""
        history = self._history[track_id]
        if len(history) < 10:
            return {
                "status": "CALIBRATING",
                "message": f"Acumulando frames para calibração: {len(history)}/10",
            }

        # 1. Análise de Mobilidade Geral
        hip_positions = self._extract_positions_by_index(history, self.KP_HIP)
        total_distance = self._calculate_total_distance(hip_positions)

        time_delta = (history[-1]["timestamp"] - history[0]["timestamp"]).total_seconds()
        avg_velocity = total_distance / time_delta if time_delta > 0 else 0.0

        # Heurística de letargia: pouco movimento em intervalo de tempo representativo
        is_lethargic = len(hip_positions) >= 10 and total_distance < 8.0 and time_delta >= 1.5

        # 2. Análise de Marcha e Coxeira (Claudicação)
        gait_score, claudication_detected = self._calculate_gait_score_and_claudication(history)

        return {
            "status": "ANALYZED",
            "track_id": track_id,
            "mobility_status": self._determine_mobility_status(claudication_detected, is_lethargic),
            "gait_score": gait_score,
            "total_distance_px": round(total_distance, 1),
            "avg_velocity_px_s": round(avg_velocity, 1),
            "claudication_detected": claudication_detected,
            "is_lethargic": is_lethargic,
            "timestamp": history[-1]["timestamp"].isoformat(),
        }
