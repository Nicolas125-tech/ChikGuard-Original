import logging
import time
from collections import deque

import numpy as np

logger = logging.getLogger(__name__)


class LamenessDetector:
    def __init__(
        self,
        model_path="yolov8n-pose.engine",
        history_size=45,
        angle_threshold=60.0,
        stride_threshold=0.05,
    ):
        """
        Inicializa o detector avançado de claudicação (Enterprise Edition).

        Args:
            model_path (str): Caminho para o modelo YOLOv8 pose (idealmente TensorRT .engine para borda).
            history_size (int): Quantidade de frames (histórico temporal) para análise da marcha.
            angle_threshold (float): Ângulo em graus. Limite de detecção (default legacy: 60.0 para compatibilidade, padrão zootécnico: 110.0).
            stride_threshold (float): Limite inferior para passada normalizada (Euclidiana). Menor que isso indica passos anormais.
        """
        from ultralytics import YOLO

        # TensorRT / ONNX para Edge Device
        self.model = YOLO(model_path, task="pose")
        self.history_size = history_size
        self.angle_threshold = angle_threshold
        self.stride_threshold = stride_threshold

        self.track_history = {}

    def process_frame(self, frame, camera_id):
        # Para evitar perda de ID por oclusão, o tracker.yaml deve ter tracker.track_buffer alto e boas métricas de re-ID.
        results = self.model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)
        events = []

        result = results[0]
        if (
            result.boxes is not None
            and result.boxes.id is not None
            and result.keypoints is not None
        ):
            track_ids = result.boxes.id.int().cpu().tolist()
            keypoints = result.keypoints.xyn.cpu().numpy()

            for track_id, kp in zip(track_ids, keypoints):
                self._update_history(track_id, kp)

                # Análise profunda após preencher a janela temporal
                if len(self.track_history[track_id]) >= (self.history_size * 0.8):
                    is_lame, conf_score, details = self.analyze_gait(track_id)
                    if is_lame:
                        events.append(self._emit_event(camera_id, track_id, conf_score, details))
                        self.track_history[track_id].clear()

        return result, events

    def _update_history(self, track_id, keypoints):
        if track_id not in self.track_history:
            self.track_history[track_id] = deque(maxlen=self.history_size)
        self.track_history[track_id].append(keypoints)

    def calculate_hock_angle(self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        """
        Calcula o ângulo Tibiotársico (Hock Angle) formando pelos pontos p1 (Quadril/Pélvis),
        p2 (Jarrete/Hock) e p3 (Pata).

        Aplica a fórmula vetorial do produto escalar:
        theta = arccos((u . v) / (|u| * |v|))

        Args:
            p1 (np.ndarray): Coordenadas [x, y] do Quadril.
            p2 (np.ndarray): Coordenadas [x, y] da Articulação Central (origem dos vetores).
            p3 (np.ndarray): Coordenadas [x, y] da Pata.

        Returns:
            float: O ângulo em graus.
        """
        # Vetor u: do jarrete para a pélvis
        u = p1 - p2
        # Vetor v: do jarrete para a pata
        v = p3 - p2

        norm_u = np.linalg.norm(u)
        norm_v = np.linalg.norm(v)

        # Salvaguarda contra divisão por zero (pontos sobrepostos ou não detectados)
        if norm_u == 0.0 or norm_v == 0.0:
            return 0.0

        dot_product = np.dot(u, v)

        # Clip garante que o valor fique entre -1 e 1 para evitar NaN no arccos devido à precisão de float
        cosine_angle = np.clip(dot_product / (norm_u * norm_v), -1.0, 1.0)
        angle_rad = np.arccos(cosine_angle)

        return float(np.degrees(angle_rad))

    def _get_leg_skeleton_mapping(self, num_kps: int) -> list[tuple[str, int, int, int]]:
        """Mapeamento do esqueleto adaptado ao modelo de Pose detectado."""
        if num_kps == 17:
            return [("Esquerda", 11, 13, 15), ("Direita", 12, 14, 16)]
        elif num_kps == 11:
            return [("Esquerda", 6, 7, 9), ("Direita", 6, 8, 10)]
        else:
            return [("Principal", 2, 3, 5)]

    def _extract_leg_angles(
        self, history: list, legs: list[tuple[str, int, int, int]]
    ) -> dict[str, list[float]]:
        """Coleta os ângulos por perna a partir do histórico de keypoints."""
        angles_per_leg = {leg_name: [] for leg_name, _, _, _ in legs}

        for curr_kp in history:
            for leg_name, hip_idx, hock_idx, foot_idx in legs:
                if (
                    hip_idx < len(curr_kp)
                    and hock_idx < len(curr_kp)
                    and foot_idx < len(curr_kp)
                ):
                    pt_hip = curr_kp[hip_idx]
                    pt_hock = curr_kp[hock_idx]
                    pt_foot = curr_kp[foot_idx]

                    hip_ok = pt_hip[0] > 0 and (len(pt_hip) < 3 or pt_hip[2] > 0.3)
                    hock_ok = pt_hock[0] > 0 and (len(pt_hock) < 3 or pt_hock[2] > 0.3)
                    foot_ok = pt_foot[0] > 0 and (len(pt_foot) < 3 or pt_foot[2] > 0.3)

                    if hip_ok and hock_ok and foot_ok:
                        p1 = np.array(pt_hip[:2])
                        p2 = np.array(pt_hock[:2])
                        p3 = np.array(pt_foot[:2])

                        angle = self.calculate_hock_angle(p1, p2, p3)
                        if angle > 0:
                            angles_per_leg[leg_name].append(angle)

        return {name: vals for name, vals in angles_per_leg.items() if len(vals) >= 15}

    def _evaluate_gait_diagnostics(
        self, valid_legs: dict[str, list[float]]
    ) -> tuple[bool, float, dict, list[str]]:
        """Calcula métricas de marcha para pernas válidas e avalia claudicação e assimetria."""
        gait_diagnostics = {}
        is_lame = False
        max_conf_score = 0.0
        symptoms = []

        for leg_name, angles in valid_legs.items():
            avg_angle = float(np.mean(angles))
            var_angle = float(np.var(angles))

            leg_lame = False
            if avg_angle < self.angle_threshold and var_angle < 5.0:
                leg_lame = True
                is_lame = True
                conf_score = float(max(0.5, 1.0 - (var_angle / 5.0)))
                max_conf_score = max(max_conf_score, conf_score)
                symptoms.append(
                    f"Claudicação na perna {leg_name}: agachamento severo (ângulo médio {avg_angle:.1f}°) "
                    f"E rigidez articular (variância {var_angle:.2f})"
                )

            gait_diagnostics[leg_name] = {
                "avg_angle": round(avg_angle, 2),
                "var_angle": round(var_angle, 2),
                "is_lame": leg_lame,
            }

        if "Esquerda" in valid_legs and "Direita" in valid_legs:
            avg_left = gait_diagnostics["Esquerda"]["avg_angle"]
            avg_right = gait_diagnostics["Direita"]["avg_angle"]
            angle_diff = abs(avg_left - avg_right)

            if angle_diff > 20.0 and not is_lame:
                is_lame = True
                max_conf_score = max(max_conf_score, float(min(0.9, angle_diff / 40.0)))
                symptoms.append(
                    f"Claudicação Unilateral: Assimetria severa de angulação intertársica ({angle_diff:.1f}° de diferença)"
                )
            gait_diagnostics["asymmetry_diff_deg"] = round(angle_diff, 2)

        return is_lame, max_conf_score, gait_diagnostics, symptoms

    def _build_gait_details(self, gait_diagnostics: dict, symptoms: list[str]) -> dict:
        """Monta o dicionário de detalhes do diagnóstico da marcha."""
        symptom_desc = "; ".join(symptoms) if symptoms else None

        avg_angles_all = [
            diag["avg_angle"]
            for diag in gait_diagnostics.values()
            if isinstance(diag, dict) and "avg_angle" in diag
        ]
        var_angles_all = [
            diag["var_angle"]
            for diag in gait_diagnostics.values()
            if isinstance(diag, dict) and "var_angle" in diag
        ]

        return {
            "avg_hock_angle": round(float(np.mean(avg_angles_all)), 2) if avg_angles_all else 0.0,
            "angle_variance": round(float(np.mean(var_angles_all)), 2) if var_angles_all else 0.0,
            "symptom": symptom_desc,
            "legs_detail": gait_diagnostics,
        }

    def analyze_gait(self, track_id: int) -> tuple[bool, float, dict]:
        """
        Heurística rigorosa de detecção de claudicação (Lameness).

        Baseia-se na biometria do Ângulo Tibiotársico (Hock Angle) calculado ao longo do tempo.
        Resolução dinâmica do esqueleto com base no número de keypoints para suportar múltiplos modelos.

        Regra de Negócio Biomecânica:
        - Ave sentada/agachada (agachamento crônico): Média histórica do ângulo < angle_threshold (default legacy: 60.0)
        - Perna travada/rigidez articular (baixa mobilidade): Variância do ângulo < 5.0

        Ambos os critérios devem ser satisfeitos simultaneamente para disparar o diagnóstico positivo.

        Args:
            track_id (int): ID da ave rastreada pelo ByteTrack.

        Returns:
            tuple[bool, float, dict]: (is_lame, confidence_score, details_dict)
        """
        history = list(self.track_history[track_id])
        if not history:
            return False, 0.0, {}

        num_kps = len(history[0])
        legs = self._get_leg_skeleton_mapping(num_kps)
        valid_legs = self._extract_leg_angles(history, legs)

        if not valid_legs:
            return False, 0.0, {}

        is_lame, max_conf_score, gait_diagnostics, symptoms = self._evaluate_gait_diagnostics(
            valid_legs
        )
        details = self._build_gait_details(gait_diagnostics, symptoms)

        return is_lame, max_conf_score, details


    def analyze_gait_advanced(self, track_id: int) -> tuple[bool, float, dict]:
        """Método legado. Delega para a nova implementação estrita analyze_gait."""
        return self.analyze_gait(track_id)

    def _emit_event(self, camera_id, track_id, confidence, details):
        event = {
            "timestamp": time.time(),
            "camera_id": str(camera_id),
            "bird_id": int(track_id),
            "event_type": "SUSPECTED_LAMENESS",
            "confidence": round(float(confidence), 3),
            "metadata": details,
        }
        return event
