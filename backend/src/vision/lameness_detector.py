import numpy as np
from collections import deque
import json
import time
import logging

logger = logging.getLogger(__name__)

class LamenessDetector:
    def __init__(self, model_path="yolov8n-pose.engine", history_size=45, angle_threshold=110.0, stride_threshold=0.05):
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
        self.model = YOLO(model_path, task='pose')
        self.history_size = history_size
        self.angle_threshold = angle_threshold
        self.stride_threshold = stride_threshold
        
        self.track_history = {}
        
    def process_frame(self, frame, camera_id):
        # Para evitar perda de ID por oclusão, o tracker.yaml deve ter tracker.track_buffer alto e boas métricas de re-ID.
        results = self.model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)
        events = []
        
        result = results[0]
        if result.boxes is not None and result.boxes.id is not None and result.keypoints is not None:
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
        
    def _calculate_angle(self, p1, p2, p3):
        """
        Calcula o ângulo (Hock Angle) formando pelos pontos p1 (pélvis), p2 (junta) e p3 (pata).
        Baseado no dot product: theta = arccos((u . v) / (|u| * |v|))
        """
        # Vetor u: junta para pélvis
        u = np.array(p1) - np.array(p2)
        # Vetor v: junta para pata
        v = np.array(p3) - np.array(p2)
        
        # Produto escalar e magnitudes
        dot_product = np.dot(u, v)
        norm_u = np.linalg.norm(u)
        norm_v = np.linalg.norm(v)
        
        if norm_u == 0 or norm_v == 0:
            return 0.0
            
        # Clipping para evitar erros de precisão do float no arccos
        cosine_angle = np.clip(dot_product / (norm_u * norm_v), -1.0, 1.0)
        angle_rad = np.arccos(cosine_angle)
        
        return np.degrees(angle_rad)

    def analyze_gait(self, track_id):
        """
        Heurística avançada por biometria geométrica:
        1. Avalia o Ângulo da Articulação (Hock Angle).
        2. Avalia o Tamanho da Passada (Stride Length Euclidiana).
        """
        history = list(self.track_history[track_id])
        
        # Índices MOCK: Assumindo mapeamento do modelo avícola
        # L = Esquerda, R = Direita
        PELVIS_L, PELVIS_R = 2, 3
        HOCK_L, HOCK_R = 4, 5     # Junta central (Articulação Tibiotársica)
        FOOT_L, FOOT_R = 6, 7
        
        angles_l, angles_r = [], []
        strides_l, strides_r = [], []
        
        for i in range(len(history)):
            curr_kp = history[i]
            
            # Filtra pontos perdidos (x ou y == 0.0 normalmente)
            if curr_kp[PELVIS_L][0] > 0 and curr_kp[HOCK_L][0] > 0 and curr_kp[FOOT_L][0] > 0:
                angle = self._calculate_angle(curr_kp[PELVIS_L], curr_kp[HOCK_L], curr_kp[FOOT_L])
                angles_l.append(angle)
            
            if curr_kp[PELVIS_R][0] > 0 and curr_kp[HOCK_R][0] > 0 and curr_kp[FOOT_R][0] > 0:
                angle = self._calculate_angle(curr_kp[PELVIS_R], curr_kp[HOCK_R], curr_kp[FOOT_R])
                angles_r.append(angle)
                
            # Cálculo de passada em relação ao frame anterior
            if i > 0:
                prev_kp = history[i-1]
                if curr_kp[FOOT_L][0] > 0 and prev_kp[FOOT_L][0] > 0:
                    stride = np.linalg.norm(curr_kp[FOOT_L] - prev_kp[FOOT_L])
                    strides_l.append(stride)
                    
                if curr_kp[FOOT_R][0] > 0 and prev_kp[FOOT_R][0] > 0:
                    stride = np.linalg.norm(curr_kp[FOOT_R] - prev_kp[FOOT_R])
                    strides_r.append(stride)

        # Se houver muita oclusão (poucos pontos válidos na janela), abortamos para evitar Falsos Positivos
        if len(angles_l) < 10 or len(angles_r) < 10:
            return False, 0.0, {}

        # Média dos ângulos
        avg_angle_l = np.mean(angles_l)
        avg_angle_r = np.mean(angles_r)
        
        # Média do deslocamento total das pernas (passadas)
        avg_stride_l = np.mean(strides_l) if strides_l else 0.0
        avg_stride_r = np.mean(strides_r) if strides_r else 0.0

        is_lame = False
        conf_score = 0.0
        symptom = None
        
        # Cenário 1: Ângulo do jarrete severamente fechado (ave sentada / dor extrema)
        if avg_angle_l < self.angle_threshold or avg_angle_r < self.angle_threshold:
            is_lame = True
            # Confiança escala com a gravidade do fechamento do ângulo
            min_ang = min(avg_angle_l, avg_angle_r)
            conf_score = max(0.5, 1.0 - (min_ang / self.angle_threshold))
            symptom = "Angulação severa (possível ajoelhamento)"

        # Cenário 2: Passada encurtada assimétrica (arrasto / hesitação)
        # Se uma das pernas se move muito menos que a normal
        stride_ratio = min(avg_stride_l, avg_stride_r) / max(avg_stride_l, avg_stride_r, 1e-6)
        if not is_lame and (avg_stride_l > 0 and avg_stride_r > 0) and stride_ratio < 0.4:
            is_lame = True
            conf_score = 1.0 - stride_ratio
            symptom = "Passada curta/assimétrica (arrasto)"

        details = {
            "avg_angle_L": round(float(avg_angle_l), 2),
            "avg_angle_R": round(float(avg_angle_r), 2),
            "stride_ratio": round(float(stride_ratio), 2),
            "symptom": symptom
        }

        return is_lame, conf_score, details

    def _emit_event(self, camera_id, track_id, confidence, details):
        event = {
            "timestamp": time.time(),
            "camera_id": str(camera_id),
            "bird_id": int(track_id),
            "event_type": "SUSPECTED_LAMENESS",
            "confidence": round(float(confidence), 3),
            "metadata": details
        }
        return event
