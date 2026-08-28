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

        if len(keypoints) < 6:
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
            kps = frame["keypoints"]
            if kp_index < len(kps):
                kp = kps[kp_index]
                if len(kp) >= 3:
                    if kp[2] > min_conf and kp[0] > 0:
                        positions.append(np.array([kp[0], kp[1]]))
                else:
                    if kp[0] > 0:
                        positions.append(np.array([kp[0], kp[1]]))
        return positions

    def _calculate_total_distance(self, positions: List[np.ndarray]) -> float:
        """Calcula o deslocamento euclidiano cumulativo a partir de uma lista de pontos."""
        if len(positions) < 2:
            return 0.0
        diffs = [positions[i] - positions[i - 1] for i in range(1, len(positions))]
        return sum(np.linalg.norm(d) for d in diffs)

    def _calculate_gait_score_and_claudication(
        self, history: List[Dict[str, Any]], hip_idx: int, lfoot_idx: int, rfoot_idx: int
    ) -> Tuple[float, bool]:
        """Calcula a assimetria da amplitude do passo e indica a presença de claudicação."""
        left_extensions = []
        right_extensions = []

        for frame in history:
            kps = frame["keypoints"]
            if hip_idx < len(kps) and lfoot_idx < len(kps) and rfoot_idx < len(kps):
                kp_hip = kps[hip_idx]
                kp_lfoot = kps[lfoot_idx]
                kp_rfoot = kps[rfoot_idx]

                # Confiança mínima recomendada para os três pontos simultaneamente
                hip_ok = kp_hip[0] > 0 and (len(kp_hip) < 3 or kp_hip[2] > 0.4)
                lfoot_ok = kp_lfoot[0] > 0 and (len(kp_lfoot) < 3 or kp_lfoot[2] > 0.4)
                rfoot_ok = kp_rfoot[0] > 0 and (len(kp_rfoot) < 3 or kp_rfoot[2] > 0.4)

                if hip_ok and lfoot_ok and rfoot_ok:
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
        claudication_detected = bool(asymmetry_ratio > 0.25)  # Mais de 25% de assimetria indica coxeira

        return gait_score, claudication_detected

    def calculate_hock_angle(self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        """Calcula o ângulo formado por p1 (Hip), p2 (Knee/Hock) e p3 (Foot)."""
        u = p1 - p2
        v = p3 - p2
        norm_u = np.linalg.norm(u)
        norm_v = np.linalg.norm(v)
        if norm_u == 0.0 or norm_v == 0.0:
            return 0.0
        cosine_angle = np.clip(np.dot(u, v) / (norm_u * norm_v), -1.0, 1.0)
        return float(np.degrees(np.arccos(cosine_angle)))

    def _calculate_hock_angles(
        self, history: List[Dict[str, Any]], hip_idx: int, lknee_idx: int, lfoot_idx: int, rknee_idx: int, rfoot_idx: int
    ) -> Tuple[float, float, float]:
        """Calcula a angulação do jarrete esquerda, direita e a média."""
        left_angles = []
        right_angles = []

        for frame in history:
            kps = frame["keypoints"]
            
            # Left leg
            if hip_idx < len(kps) and lknee_idx < len(kps) and lfoot_idx < len(kps):
                pt_hip = kps[hip_idx]
                pt_knee = kps[lknee_idx]
                pt_foot = kps[lfoot_idx]
                
                hip_ok = pt_hip[0] > 0 and (len(pt_hip) < 3 or pt_hip[2] > 0.3)
                knee_ok = pt_knee[0] > 0 and (len(pt_knee) < 3 or pt_knee[2] > 0.3)
                foot_ok = pt_foot[0] > 0 and (len(pt_foot) < 3 or pt_foot[2] > 0.3)
                
                if hip_ok and knee_ok and foot_ok:
                    p1 = np.array(pt_hip[:2])
                    p2 = np.array(pt_knee[:2])
                    p3 = np.array(pt_foot[:2])
                    angle = self.calculate_hock_angle(p1, p2, p3)
                    if angle > 0:
                        left_angles.append(angle)
            
            # Right leg
            if hip_idx < len(kps) and rknee_idx < len(kps) and rfoot_idx < len(kps):
                pt_hip = kps[hip_idx]
                pt_knee = kps[rknee_idx]
                pt_foot = kps[rfoot_idx]
                
                hip_ok = pt_hip[0] > 0 and (len(pt_hip) < 3 or pt_hip[2] > 0.3)
                knee_ok = pt_knee[0] > 0 and (len(pt_knee) < 3 or pt_knee[2] > 0.3)
                foot_ok = pt_foot[0] > 0 and (len(pt_foot) < 3 or pt_foot[2] > 0.3)
                
                if hip_ok and knee_ok and foot_ok:
                    p1 = np.array(pt_hip[:2])
                    p2 = np.array(pt_knee[:2])
                    p3 = np.array(pt_foot[:2])
                    angle = self.calculate_hock_angle(p1, p2, p3)
                    if angle > 0:
                        right_angles.append(angle)

        avg_l = float(np.mean(left_angles)) if left_angles else 0.0
        avg_r = float(np.mean(right_angles)) if right_angles else 0.0
        
        valid_angles = [a for a in [avg_l, avg_r] if a > 0]
        avg_all = float(np.mean(valid_angles)) if valid_angles else 0.0

        return avg_l, avg_r, avg_all

    def _calculate_lateral_sway(self, positions: List[np.ndarray]) -> float:
        """Calcula o desvio perpendicular padrão (oscilação lateral) em relação à linha de movimento."""
        if len(positions) < 5:
            return 0.0
            
        p_start = positions[0]
        p_end = positions[-1]
        vec = p_end - p_start
        norm = np.linalg.norm(vec)
        
        if norm < 5.0:
            x_coords = [p[0] for p in positions]
            return float(np.std(x_coords))
            
        dx = p_end[0] - p_start[0]
        dy = p_end[1] - p_start[1]
        
        distances = []
        for p in positions:
            dist = abs(dy * p[0] - dx * p[1] + dx * p_start[1] - dy * p_start[0]) / norm
            distances.append(dist)
            
        return float(np.std(distances))

    def _calculate_kestin_gait_score(
        self, asymmetry: float, avg_hock_angle: float, sway_ratio: float, is_lethargic: bool
    ) -> Tuple[int, str]:
        """
        Determina o Score de Marcha de Kestin (0 a 5) baseado em parâmetros zootécnicos.
        """
        if is_lethargic and (avg_hock_angle < 70.0 and avg_hock_angle > 0.0):
            return 5, "Não ambulatório (incapaz de levantar, ângulo crítico de jarrete)"
            
        score = 0
        
        # 1. Contribuição de assimetria do passo
        if asymmetry > 0.45:
            score = max(score, 4)
        elif asymmetry > 0.30:
            score = max(score, 3)
        elif asymmetry > 0.20:
            score = max(score, 2)
        elif asymmetry > 0.12:
            score = max(score, 1)
            
        # 2. Contribuição do ângulo de jarrete
        if avg_hock_angle > 0:
            if avg_hock_angle < 75.0:
                score = max(score, 5)
            elif avg_hock_angle < 90.0:
                score = max(score, 4)
            elif avg_hock_angle < 105.0:
                score = max(score, 3)
            elif avg_hock_angle < 120.0:
                score = max(score, 2)
            elif avg_hock_angle < 135.0:
                score = max(score, 1)
                
        # 3. Contribuição de oscilação lateral
        if sway_ratio > 0.25:
            score = max(score, 3)
        elif sway_ratio > 0.15:
            score = max(score, 2)
        elif sway_ratio > 0.08:
            score = max(score, 1)
            
        # 4. Caso a ave esteja prostrada/letárgica
        if is_lethargic and score < 3:
            score = 3
            
        descriptions = {
            0: "Marcha Normal e saudável. Passos simétricos e boa sustentação.",
            1: "Alteração Leve. Pequeno desvio de simetria ou postura levemente encurvada.",
            2: "Claudicação Leve. Coxeira identificável; ave caminha com leve dificuldade.",
            3: "Claudicação Moderada. Dificuldade de locomoção significativa e pausas frequentes.",
            4: "Claudicação Severa. Ave caminha apenas sob forte estímulo; postura muito agachada.",
            5: "Não Ambulatório. Paralisia ou agachamento crônico severo (decúbito)."
        }
        
        return score, descriptions.get(score, "Status desconhecido")

    def _determine_mobility_status(self, claudication_detected: bool, is_lethargic: bool, kestin_score: int) -> str:
        """Determina o status clínico simplificado com base nas detecções."""
        if is_lethargic:
            return "LETARGIA_APATIA"
        if claudication_detected:
            return "CLAUDICACAO_DETECTADA"
        return "NORMAL"

    def _resolve_keypoint_indices(self, num_kps: int) -> Dict[str, int]:
        """Resolve os índices dos keypoints com base na estrutura do esqueleto detectada."""
        if num_kps >= 17:  # COCO
            return {
                "hip_idx": 11,
                "lknee_idx": 13,
                "rknee_idx": 14,
                "lfoot_idx": 15,
                "rfoot_idx": 16,
                "neck_idx": 0,
            }
        elif num_kps >= 11:  # ChikGuard
            return {
                "hip_idx": 6,
                "lknee_idx": 7,
                "rknee_idx": 8,
                "lfoot_idx": 9,
                "rfoot_idx": 10,
                "neck_idx": 3,
            }
        elif num_kps >= 6:  # Custom Simplificado
            return {
                "hip_idx": 2,
                "lknee_idx": 3,
                "rknee_idx": 3,
                "lfoot_idx": 5,
                "rfoot_idx": 5,
                "neck_idx": 0,
            }
        else:
            return {
                "hip_idx": 0,
                "lknee_idx": 0,
                "rknee_idx": 0,
                "lfoot_idx": 0,
                "rfoot_idx": 0,
                "neck_idx": 0,
            }

    def _calculate_sway_metrics(
        self, history: List[Dict[str, Any]], num_kps: int, hip_idx: int, neck_idx: int, lfoot_idx: int
    ) -> Tuple[float, float]:
        """Calcula a oscilação lateral e a razão de oscilação normalizada."""
        sway_positions = self._extract_positions_by_index(history, neck_idx if num_kps >= 11 else hip_idx)
        lateral_sway = self._calculate_lateral_sway(sway_positions)

        ref_extensions = []
        for frame in history:
            kps = frame["keypoints"]
            if hip_idx < len(kps) and lfoot_idx < len(kps):
                pt_hip = kps[hip_idx]
                pt_foot = kps[lfoot_idx]
                if pt_hip[0] > 0 and pt_foot[0] > 0:
                    ref_extensions.append(np.linalg.norm(np.array(pt_foot[:2]) - np.array(pt_hip[:2])))

        avg_ref_size = float(np.mean(ref_extensions)) if ref_extensions else 1.0
        sway_ratio = lateral_sway / avg_ref_size if avg_ref_size > 0 else 0.0
        return lateral_sway, sway_ratio

    def _analyze_individual(self, track_id: int) -> Dict[str, Any]:
        """Executa a análise biomecânica global para o track do animal."""
        history = self._history[track_id]
        if len(history) < 10:
            return {
                "status": "CALIBRATING",
                "message": f"Acumulando frames para calibração: {len(history)}/10",
            }

        # Resolução de esqueleto baseada no tamanho dos keypoints
        num_kps = len(history[0]["keypoints"])
        kp_indices = self._resolve_keypoint_indices(num_kps)
        hip_idx = kp_indices["hip_idx"]
        lknee_idx = kp_indices["lknee_idx"]
        rknee_idx = kp_indices["rknee_idx"]
        lfoot_idx = kp_indices["lfoot_idx"]
        rfoot_idx = kp_indices["rfoot_idx"]
        neck_idx = kp_indices["neck_idx"]

        # 1. Análise de Mobilidade Geral
        hip_positions = self._extract_positions_by_index(history, hip_idx)
        total_distance = self._calculate_total_distance(hip_positions)

        time_delta = (history[-1]["timestamp"] - history[0]["timestamp"]).total_seconds()
        avg_velocity = total_distance / time_delta if time_delta > 0 else 0.0

        is_lethargic = bool(len(hip_positions) >= 10 and total_distance < 8.0 and time_delta >= 1.4)

        # 2. Análise de Marcha e Coxeira (Claudicação)
        gait_score, claudication_detected = self._calculate_gait_score_and_claudication(
            history, hip_idx, lfoot_idx, rfoot_idx
        )

        # 3. Análise de Ângulos de Jarrete (Hock Angles)
        avg_hock_l, avg_hock_r, avg_hock_all = self._calculate_hock_angles(
            history, hip_idx, lknee_idx, lfoot_idx, rknee_idx, rfoot_idx
        )

        # 4. Análise de Oscilação Lateral (Lateral Sway)
        lateral_sway, sway_ratio = self._calculate_sway_metrics(
            history, num_kps, hip_idx, neck_idx, lfoot_idx
        )

        # 5. Classificação Zootécnica de Marcha de Kestin
        kestin_score, kestin_desc = self._calculate_kestin_gait_score(
            gait_score, avg_hock_all, sway_ratio, is_lethargic
        )

        return {
            "status": "ANALYZED",
            "track_id": track_id,
            "mobility_status": self._determine_mobility_status(claudication_detected, is_lethargic, kestin_score),
            "gait_score": gait_score,
            "total_distance_px": round(total_distance, 1),
            "avg_velocity_px_s": round(avg_velocity, 1),
            "claudication_detected": claudication_detected,
            "is_lethargic": is_lethargic,
            "timestamp": history[-1]["timestamp"].isoformat(),
            
            # Novos campos enriquecidos
            "kestin_gait_score": kestin_score,
            "kestin_description": kestin_desc,
            "avg_hock_angle_left": round(avg_hock_l, 2),
            "avg_hock_angle_right": round(avg_hock_r, 2),
            "avg_hock_angle_combined": round(avg_hock_all, 2),
            "lateral_sway_px": round(lateral_sway, 2),
            "sway_ratio": round(sway_ratio, 3),
            "skeletal_format_detected": "COCO-17" if num_kps == 17 else ("ChikGuard-11" if num_kps == 11 else f"Custom-{num_kps}")
        }
