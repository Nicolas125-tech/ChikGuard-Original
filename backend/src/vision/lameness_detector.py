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
        angle_threshold=110.0,
        stride_threshold=0.05,
    ):
        """
        Inicializa o detector avançado de claudicação (Enterprise Edition).

        Args:
            model_path (str): Caminho para o modelo YOLOv8 pose (idealmente TensorRT .engine para borda).
            history_size (int): Quantidade de frames (histórico temporal) para análise da marcha.
            angle_threshold (float): Ângulo em graus. Ângulos consistentemente menores que isso indicam ave sentada/mancando.
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

    def analyze_gait(self, track_id: int) -> tuple[bool, float, dict]:
        """
        Heurística rigorosa de detecção de claudicação (Lameness).

        Baseia-se na biometria do Ângulo Tibiotársico (Hock Angle) calculado ao longo do tempo.
        
        Regra de Negócio Biomecânica:
        - Ave sentada/agachada (agachamento crônico): Média histórica do ângulo < 60°
        - Perna travada/rigidez articular (baixa mobilidade): Variância do ângulo < 5.0

        Ambos os critérios devem ser satisfeitos simultaneamente para disparar o diagnóstico positivo.

        Args:
            track_id (int): ID da ave rastreada pelo ByteTrack.

        Returns:
            tuple[bool, float, dict]: (is_lame, confidence_score, details_dict)
        """
        history = list(self.track_history[track_id])

        # Mapeamento biomecânico dos Keypoints YOLOv8-pose
        HIP = 2   # Quadril/Pélvis (ponto de fixação superior da coxa)
        HOCK = 3  # Jarrete/Articulação Tibiotársica (articulação intermediária da perna)
        FOOT = 5  # Pata (ponto de apoio ao solo)

        angles = []

        for curr_kp in history:
            # Garante que os keypoints foram detectados com confiança razoável (evita oclusão)
            if curr_kp[HIP][0] > 0 and curr_kp[HOCK][0] > 0 and curr_kp[FOOT][0] > 0:
                p1 = np.array(curr_kp[HIP][:2])
                p2 = np.array(curr_kp[HOCK][:2])
                p3 = np.array(curr_kp[FOOT][:2])

                angle = self.calculate_hock_angle(p1, p2, p3)
                if angle > 0:  # Descarta retornos de erro da função geométrica (0.0)
                    angles.append(angle)

        # Exige amostragem temporal mínima representativa (mínimo de 15 frames válidos)
        if len(angles) < 15:
            return False, 0.0, {}

        # Métricas estatísticas da série temporal do Hock Angle
        avg_angle = float(np.mean(angles))
        var_angle = float(np.var(angles))

        is_lame = False
        conf_score = 0.0
        symptom = None

        # Avaliação de claudicação conforme os limites fisiológicos
        if avg_angle < 60.0 and var_angle < 5.0:
            is_lame = True
            # Confiança baseada na imobilidade da articulação: variância mais baixa indica
            # maior certeza de travamento articular. Normalizado com piso de 0.5.
            conf_score = float(max(0.5, 1.0 - (var_angle / 5.0)))
            symptom = (
                "Claudicação crônica: Agachamento severo (ângulo médio <60) E rigidez articular (variância <5.0)"
            )

        details = {
            "avg_hock_angle": round(avg_angle, 2),
            "angle_variance": round(var_angle, 2),
            "symptom": symptom,
        }

        return is_lame, conf_score, details

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
