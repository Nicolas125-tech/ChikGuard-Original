import cv2
import numpy as np
import os
import time
import logging

LOGGER = logging.getLogger(__name__)

class ActiveLearningPipeline:
    def __init__(self, output_dir="data/active_learning", min_conf=0.30, max_conf=0.45):
        self.output_dir = output_dir
        self.min_conf = min_conf
        self.max_conf = max_conf
        os.makedirs(self.output_dir, exist_ok=True)
        # Tenta carregar o modelo de face do OpenCV
        self.face_cascade = None
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            LOGGER.error(f"Erro ao carregar face cascade: {e}")

    def process_detection(self, frame, detection, class_name):
        # Apenas processa se for a classe alvo
        target_names = ["bird", "ave", "chicken", "galinha", "frango"]
        if class_name.lower() not in target_names:
            return

        conf = detection.get("confidence", 1.0)

        # Se a confianca esta na zona de incerteza
        if self.min_conf <= conf <= self.max_conf:
            self._save_uncertain_frame(frame.copy(), detection, conf)

    def _save_uncertain_frame(self, frame, detection, conf):
        try:
            # 1. Ofuscar rostos humanos (Privacidade/IP)
            if self.face_cascade is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
                for (x, y, w, h) in faces:
                    # Aplica blur pesado no rosto
                    face_roi = frame[y:y+h, x:x+w]
                    frame[y:y+h, x:x+w] = cv2.GaussianBlur(face_roi, (99, 99), 30)

            # 2. Recortar a deteccao com margem (contexto)
            x1, y1, x2, y2 = [int(v) for v in detection["box"]]
            pad = 100 # pixels de margem
            h, w = frame.shape[:2]
            cx1 = max(0, x1 - pad)
            cy1 = max(0, y1 - pad)
            cx2 = min(w, x2 + pad)
            cy2 = min(h, y2 + pad)

            crop = frame[cy1:cy2, cx1:cx2]

            # 3. Salvar localmente
            ts = int(time.time() * 1000)
            filename = f"uncertain_{ts}_conf_{conf:.2f}.jpg"
            filepath = os.path.join(self.output_dir, filename)

            cv2.imwrite(filepath, crop)
            LOGGER.info(f"MLOps: Saved active learning sample (conf: {conf:.2f}) to {filepath}")
        except Exception as e:
            LOGGER.error(f"Erro no pipeline de Active Learning: {e}")

    def sync_to_cloud(self):
        """Simula o envio noturno para a nuvem da ChikGuard"""
        LOGGER.info("Starting night sync: Active Learning Data -> ChikGuard Cloud...")
        try:
            files = [f for f in os.listdir(self.output_dir) if f.endswith(".jpg")]
            if not files:
                LOGGER.info("No active learning data to sync.")
                return

            for file in files:
                filepath = os.path.join(self.output_dir, file)
                # Simula upload
                LOGGER.info(f"Syncing {file} to ChikGuard Cloud for MLOps retraining...")
                os.remove(filepath) # Remove local apos sucesso para nao encher o disco
        except Exception as e:
            LOGGER.error(f"Sync failed: {e}")

active_learning_pipeline = ActiveLearningPipeline(output_dir=os.path.join(os.path.dirname(__file__), "..", "..", "data", "active_learning"))
