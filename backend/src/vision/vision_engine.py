import cv2
import time
import os
from collections import deque
import threading

class VisionEngine:
    """
    VisionEngine: Pipeline otimizado para carreamento de modelos (.engine, .xml, .onnx)
    e processamento de video com leitura assíncrona.
    """
    def __init__(self, model_path, camera_index=0):
        self.model_path = model_path
        self.camera_index = camera_index
        self.cap = None
        self.is_running = False
        self._frame_buffer = deque(maxlen=3)
        self._lock = threading.Lock()
        self._capture_thread = None
        self._load_model()

    def _load_model(self):
        """Carrega o modelo com base na extensão"""
        ext = os.path.splitext(self.model_path)[1].lower()
        if ext == '.engine':
            print(f"Carregando modelo TensorRT: {self.model_path}")
            # Placeholder for actual TensorRT loading logic
        elif ext == '.xml':
            print(f"Carregando modelo OpenVINO: {self.model_path}")
            # Placeholder for actual OpenVINO loading logic
        elif ext in ['.onnx', '.pt']:
            print(f"Carregando modelo {ext}: {self.model_path}")
            # Placeholder for existing ultralytics YOLO logic
        else:
            print(f"Aviso: Formato de modelo não suportado nativamente pelo VisionEngine: {ext}")

    def start_capture(self):
        """Inicia a captura de vídeo de forma assíncrona para evitar lag"""
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"Erro: Não foi possível abrir a câmera {self.camera_index}")
            return False

        self.is_running = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        return True

    def _capture_loop(self):
        """Loop de captura que roda em thread separada"""
        while self.is_running:
            if self.cap is not None and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    with self._lock:
                        self._frame_buffer.append(frame)
                else:
                    time.sleep(0.01) # Avoid busy loop if frame drop
            else:
                time.sleep(0.1)

    def get_latest_frame(self):
        """Retorna o frame mais recente do buffer"""
        with self._lock:
            if len(self._frame_buffer) > 0:
                return self._frame_buffer[-1].copy()
            return None

    def stop_capture(self):
        """Para a captura de vídeo"""
        self.is_running = False
        if self._capture_thread is not None:
            self._capture_thread.join(timeout=1.0)
        if self.cap is not None:
            self.cap.release()
            self.cap = None
