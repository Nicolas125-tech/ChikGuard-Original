import json
import logging
import time
from collections import deque
from typing import Any, Optional, Tuple

import numpy as np

from src.audio.audio_processor import compute_mel_spectrogram

logger = logging.getLogger("chikguard.audio.classifier")


class RespiratoryDiseaseClassifier:
    """
    Classificador focado na detecção de patologias respiratórias (ex: snicking/tosses avícolas).
    Aplica heurística de agrupamento temporal (Time-window Heuristics) para evitar alarmes falsos
    gerados por ruídos isolados na granja (ex: poeira e ventiladores).
    """

    def __init__(self, model_path: str, confidence_threshold: float = 0.70):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold

        # Heurística temporal (Sliding Window)
        self.cough_history = deque()
        self.time_window_sec = 60.0  # Janela de análise de 1 minuto
        self.min_coughs_trigger = 3  # Alarme se houver 3 tosses/espirros dentro da janela

        # Categorias de inferência (Output Layer)
        self.classes = ["HEALTHY_CHIRP", "COUGH_SNICKING", "FAN_NOISE", "UNKNOWN"]

        self.session = self._load_model()

    def _load_model(self) -> Optional[Any]:
        """
        Inicia o runtime para rodar o modelo IA leve na Borda (Edge).
        Para fins corporativos, assume-se que o arquivo é .onnx (ONNX Runtime) ou .tflite.
        """
        logger.info(
            f"Carregando modelo de classificação de áudio leve da Borda em: {self.model_path}"
        )

        # if self.model_path.endswith('.onnx'):
        #     import onnxruntime as ort
        #     return ort.InferenceSession(self.model_path)
        # elif self.model_path.endswith('.tflite'):
        #     import tflite_runtime.interpreter as tflite
        #     interpreter = tflite.Interpreter(model_path=self.model_path)
        #     interpreter.allocate_tensors()
        #     return interpreter

        return None  # Retornado como mock se nenhuma engine estiver presente

    def classify_audio_chunk(self, audio_buffer: np.ndarray, sr: int = 16000) -> Tuple[str, float]:
        """
        Recebe um fluxo contínuo de áudio (chunks de 3~5s), processa e executa a IA.

        Returns:
            Uma tupla contendo a classe predita e o índice de confiança (score).
        """
        # Extrai Espectrograma (Feature Extraction)
        mel_features = compute_mel_spectrogram(audio_buffer, sr=sr)

        # Lógica de Inferência Base (Substituído pela lógica real do TFLite/ONNX)
        # No ambiente corporativo real de IA:
        # inputs = {self.session.get_inputs()[0].name: np.expand_dims(mel_features, axis=0)}
        # outputs = self.session.run(None, inputs)
        # scores = outputs[0][0]
        # pred_idx = np.argmax(scores)
        # return self.classes[pred_idx], scores[pred_idx]

        # MOCK para fluxo de desenvolvimento: Detecta tosses baseadas na energia/pico abrupto
        peak_energy = np.max(np.abs(audio_buffer))
        detected_class = "HEALTHY_CHIRP"
        confidence = 0.85

        # Simulando uma assinatura de "Snicking/Tosse" avícola que tem alta amplitude repentina
        if peak_energy > 0.4:
            detected_class = "COUGH_SNICKING"
            confidence = min(0.99, peak_energy + 0.2)

        return detected_class, confidence

    def analyze_and_emit(
        self, audio_buffer: np.ndarray, sr: int, camera_zone: str, broker_client=None
    ):
        """
        Consome os chunks do pipeline do microserviço, avalia a classe,
        aplica a heurística para evitar ruídos isolados e dispara o evento no broker.
        """
        detected_class, confidence = self.classify_audio_chunk(audio_buffer, sr)

        now = time.time()

        # Elimina ocorrências (tosses) antigas que já saíram da janela de 60 segundos
        while self.cough_history and now - self.cough_history[0] > self.time_window_sec:
            self.cough_history.popleft()

        # Adiciona nova ocorrência na janela temporal
        if detected_class == "COUGH_SNICKING" and confidence >= self.confidence_threshold:
            self.cough_history.append(now)

        # Validação da Heurística ESG/Biossegurança
        if len(self.cough_history) >= self.min_coughs_trigger:
            self._emit_alert(camera_zone, broker_client)
            # Drena a janela após um alerta crítico para não floodar a rede / API
            self.cough_history.clear()

    def _emit_alert(self, camera_zone: str, broker_client: Optional[Any]):
        """
        Constrói o payload JSON e publica o evento estruturado no message broker (Redis/MQTT).
        Esse evento será consumido pelo backend central via Flask ou WebSocket para exibir no front.
        """
        payload = {
            "event_type": "RESPIRATORY_DISTRESS_ALERT",
            "zone_id": camera_zone,
            "timestamp": int(time.time()),
            "anomaly_type": "REPETITIVE_SNICKING",
            "severity": "CRITICAL",
            "confidence": round(self.confidence_threshold, 2),
            "message": f"Biossegurança Comprometida: Mais de {self.min_coughs_trigger} tosses detectadas na zona {camera_zone} no último minuto.",
        }

        logger.warning(f"🚨 ALERT DISPATCHED: {payload['message']}")

        if broker_client:
            try:
                # Disparo compatível com arquitetura Event-Driven (Pub/Sub)
                broker_client.publish("chikguard/telemetry/audio_alerts", json.dumps(payload))
                logger.info("Payload publicado com sucesso no message broker.")
            except Exception as e:
                logger.error(f"Falha de I/O ao notificar o Message Broker: {e}")
