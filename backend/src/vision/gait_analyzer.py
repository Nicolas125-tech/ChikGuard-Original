from typing import Dict, Any, List, Tuple
import math
import numpy as np
from datetime import datetime

class GaitAnalyzer:
    """Analisador de marcha e mobilidade individual de aves a partir de keypoints (YOLOv8-Pose).

    Analisa a trajetória e biomecânica de cada ave identificada (Track ID) para detectar
    claudicação (coxeira), fadiga ou comportamento apático (letargia).
    """
    def __init__(self, history_len: int = 30, fps: int = 15):
        self.history_len = history_len
        self.fps = fps
        # Histórico de keypoints indexado por track_id
        # Cada entrada guarda uma lista de dicionários de frames recentes contendo timestamps e keypoints
        self._history: Dict[int, List[Dict[str, Any]]] = {}

        # Mapeamento do esqueleto YOLOv8-Pose para Aves (Índices dos Keypoints)
        self.KP_BEAK = 0
        self.KP_EYE_L = 1
        self.KP_EYE_R = 2
        self.KP_NECK = 3
        self.KP_LEFT_WING = 4
        self.KP_RIGHT_WING = 5
        self.KP_HIP = 6
        self.KP_LEFT_KNEE = 7
        self.KP_RIGHT_KNEE = 8
        self.KP_LEFT_FOOT = 9
        self.KP_RIGHT_FOOT = 10

    def update_track(self, track_id: int, keypoints: List[List[float]], timestamp: datetime = None) -> Dict[str, Any]:
        """Atualiza o histórico de uma ave específica com os keypoints do frame atual.

        Args:
            track_id: Identificador único de rastreamento do animal.
            keypoints: Lista de keypoints no formato [[x, y, conf], [x, y, conf], ...]
            timestamp: Momento da leitura (caso None, usa o horário atual).
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        if len(keypoints) < 11:
            # Garante que temos a quantidade mínima de keypoints do esqueleto aviário
            return {"status": "INSUFFICIENT_KEYPOINTS"}

        if track_id not in self._history:
            self._history[track_id] = []

        self._history[track_id].append({
            "timestamp": timestamp,
            "keypoints": keypoints
        })

        # Mantém tamanho do buffer de histórico limitado
        if len(self._history[track_id]) > self.history_len:
            self._history[track_id].pop(0)

        # Roda a análise biomecânica com os dados acumulados
        return self._analyze_individual(track_id)

    def remove_track(self, track_id: int):
        """Remove o histórico de rastreamento de uma ave que saiu de quadro."""
        if track_id in self._history:
            del self._history[track_id]

    def _analyze_individual(self, track_id: int) -> Dict[str, Any]:
        """Analisa o padrão de movimento acumulado de uma ave específica."""
        history = self._history[track_id]
        if len(history) < 10:
            return {
                "status": "CALIBRATING",
                "message": f"Acumulando frames para calibração: {len(history)}/10"
            }

        # 1. Análise de Mobilidade Geral (Letargia / Apatia)
        # Calcula o deslocamento do quadril (hip) ao longo do tempo em pixels
        hip_positions = []
        for frame in history:
            kp_hip = frame["keypoints"][self.KP_HIP]
            if kp_hip[2] > 0.4: # Confiança mínima do ponto
                hip_positions.append(np.array([kp_hip[0], kp_hip[1]]))

        total_distance = 0.0
        for i in range(1, len(hip_positions)):
            total_distance += np.linalg.norm(hip_positions[i] - hip_positions[i - 1])

        time_delta = (history[-1]["timestamp"] - history[0]["timestamp"]).total_seconds()
        avg_velocity = total_distance / time_delta if time_delta > 0 else 0.0

        # Heurística de letargia: se a ave se moveu menos de 5 pixels em 2 segundos
        is_lethargic = False
        if len(hip_positions) >= 10 and total_distance < 8.0 and time_delta >= 1.5:
            is_lethargic = True

        # 2. Análise de Claudicação (Assimetria do Passo)
        # Medimos a distância de extensão de cada perna em relação ao quadril durante o ciclo de marcha
        left_extensions = []
        right_extensions = []
        for frame in history:
            kps = frame["keypoints"]
            kp_hip = kps[self.KP_HIP]
            kp_lfoot = kps[self.KP_LEFT_FOOT]
            kp_rfoot = kps[self.KP_RIGHT_FOOT]

            if kp_hip[2] > 0.4 and kp_lfoot[2] > 0.4 and kp_rfoot[2] > 0.4:
                # Vetores de extensão
                l_ext = np.linalg.norm(np.array([kp_lfoot[0], kp_lfoot[1]]) - np.array([kp_hip[0], kp_hip[1]]))
                r_ext = np.linalg.norm(np.array([kp_rfoot[0], kp_rfoot[1]]) - np.array([kp_hip[0], kp_hip[1]]))
                left_extensions.append(l_ext)
                right_extensions.append(r_ext)

        gait_score = 0.0 # 0.0 = marcha perfeita, 1.0 = claudicação severa
        claudication_detected = False
        
        if len(left_extensions) >= 5:
            # Calcula a média da amplitude de oscilação e extensão de cada pata
            avg_l_ext = sum(left_extensions) / len(left_extensions)
            avg_r_ext = sum(right_extensions) / len(right_extensions)
            
            # Razão de assimetria do passo
            if avg_l_ext > 0 and avg_r_ext > 0:
                asymmetry_ratio = abs(avg_l_ext - avg_r_ext) / max(avg_l_ext, avg_r_ext)
                gait_score = round(asymmetry_ratio, 2)
                # Se a assimetria do tamanho do passo for maior que 25%, indica lesão/claudicação
                if asymmetry_ratio > 0.25:
                    claudication_detected = True

        # Classificação do status de mobilidade
        mobility_status = "NORMAL"
        if claudication_detected:
            mobility_status = "CLAUDICACAO_DETECTADA"
        elif is_lethargic:
            mobility_status = "LETARGIA_APATIA"

        return {
            "status": "ANALYZED",
            "track_id": track_id,
            "mobility_status": mobility_status,
            "gait_score": gait_score,
            "total_distance_px": round(total_distance, 1),
            "avg_velocity_px_s": round(avg_velocity, 1),
            "claudication_detected": claudication_detected,
            "is_lethargic": is_lethargic,
            "timestamp": history[-1]["timestamp"].isoformat()
        }
