import cv2
import time
import os
from collections import deque
import threading


try:
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    SAHI_AVAILABLE = True
except ImportError:
    SAHI_AVAILABLE = False
    print("Aviso: 'sahi' não está instalado. Sliced inference será desativada.")


class VisionEngine:
    """
    VisionEngine: Pipeline otimizado para Edge Computing.
    Suporta inferência fatiada (SAHI) para detecção de pequenos objetos e segmentação de instância.
    """

    def __init__(self, model_path, camera_index=0, use_sahi=True, slice_height=512, slice_width=512,
                 overlap_height_ratio=0.2, overlap_width_ratio=0.2, confidence_threshold=0.3):
        self.model_path = model_path
        self.camera_index = camera_index
        self.cap = None
        self.is_running = False
        self._frame_buffer = deque(maxlen=3)
        self._lock = threading.Lock()
        self._capture_thread = None

        self.use_sahi = use_sahi and SAHI_AVAILABLE
        self.slice_height = slice_height
        self.slice_width = slice_width
        self.overlap_height_ratio = overlap_height_ratio
        self.overlap_width_ratio = overlap_width_ratio
        self.confidence_threshold = confidence_threshold

        # Initialize CLAHE
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        self.model_type = None
        self.model = None
        self._load_model()

    def _apply_clahe(self, frame):
        """Aplica CLAHE no canal L do espaço LAB para estabilizar iluminação"""
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        cl = self.clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    def _load_model(self):
        """Carrega o modelo base ou SAHI dependendo da configuração"""
        ext = os.path.splitext(self.model_path)[1].lower()

        if self.use_sahi:
            print(f"Carregando modelo com suporte SAHI: {self.model_path}")
            # Mapeamento do tipo de modelo para o SAHI
            if ext == '.pt':
                model_type = "yolov8"  # O SAHI lida com yolov8/v9 da mesma forma usando ultralytics no backend
            else:
                print("Aviso: Formato não testado com SAHI. Tentando carregar como YOLO.")
                model_type = "yolov8"

            try:
                self.model = AutoDetectionModel.from_pretrained(
                    model_type=model_type,
                    model_path=self.model_path,
                    confidence_threshold=self.confidence_threshold,
                    device="cpu"  # Pode ser alterado para cuda se disponível
                )
                self.model_type = "sahi"
                print("Modelo SAHI carregado com sucesso.")
            except Exception as e:
                print(f"Erro ao carregar modelo via SAHI: {e}. Fallback para carregamento direto.")
                self.use_sahi = False
                self._load_direct(ext)
        else:
            self._load_direct(ext)

    def _load_direct(self, ext):
        """Carrega o modelo diretamente caso SAHI esteja desativado ou falhe"""
        if ext == '.engine':
            print(f"Carregando modelo TensorRT diretamente: {self.model_path}")
            self.model_type = "tensorrt"
            # Placeholder for actual TensorRT loading logic

        elif ext == '.xml':
            print(f"Carregando modelo OpenVINO diretamente: {self.model_path}")
            self.model_type = "openvino"
            try:
                from openvino.runtime import Core
                ie = Core()
                model_xml = self.model_path
                model_bin = os.path.splitext(model_xml)[0] + ".bin"
                self.model = ie.read_model(model=model_xml, weights=model_bin)
                self.compiled_model = ie.compile_model(model=self.model, device_name="CPU")
                print("OpenVINO model loaded successfully.")
            except ImportError:
                print("Aviso: 'openvino' não está instalado. Não é possível carregar modelos .xml")
            except Exception as e:
                print(f"Erro ao carregar modelo OpenVINO: {e}")

        elif ext == '.onnx':
            print(f"Carregando modelo ONNX diretamente: {self.model_path}")
            self.model_type = "onnx"
            try:
                import onnxruntime as ort
                self.model = ort.InferenceSession(self.model_path, providers=['CPUExecutionProvider'])
                print("ONNX model loaded successfully.")
            except ImportError:
                print("Aviso: 'onnxruntime' não está instalado. Não é possível carregar modelos .onnx")
            except Exception as e:
                print(f"Erro ao carregar modelo ONNX: {e}")

        elif ext == '.pt':
            print(f"Carregando modelo PyTorch/YOLO diretamente: {self.model_path}")
            self.model_type = "yolo"
            try:
                from ultralytics import YOLO
                self.model = YOLO(self.model_path)
                print("YOLO model loaded successfully.")
            except ImportError:
                print("Aviso: 'ultralytics' não está instalado. Não é possível carregar modelos .pt")
            except Exception as e:
                print(f"Erro ao carregar modelo PyTorch: {e}")
        else:
            print(f"Aviso: Formato de modelo não suportado nativamente: {ext}")

    def predict(self, frame):
        """Executa inferência no frame (com CLAHE e opcionalmente SAHI)"""
        # Pré-processamento resiliente
        processed_frame = self._apply_clahe(frame)

        results = []
        if self.use_sahi and self.model_type == "sahi":
            # SAHI: Slicing Aided Hyper Inference
            prediction_result = get_sliced_prediction(
                processed_frame,
                self.model,
                slice_height=self.slice_height,
                slice_width=self.slice_width,
                overlap_height_ratio=self.overlap_height_ratio,
                overlap_width_ratio=self.overlap_width_ratio
            )
            # Retorna lista de dicts
            for obj in prediction_result.object_prediction_list:
                bbox = obj.bbox.to_xyxy()
                mask = obj.mask.bool_mask if obj.mask else None
                results.append({
                    "bbox": [int(x) for x in bbox],
                    "score": obj.score.value,
                    "category_id": obj.category.id,
                    "category_name": obj.category.name,
                    "mask": mask
                })
        else:
            # Inferência padrão (exemplo simplificado com ultralytics)
            if self.model_type == "yolo":
                res = self.model(processed_frame, conf=self.confidence_threshold, verbose=False)[0]
                for box in res.boxes:
                    b = box.xyxy[0].cpu().numpy()
                    c = int(box.cls[0].cpu().numpy())
                    s = box.conf[0].cpu().numpy()

                    # Máscara de segmentação, se houver
                    mask = None
                    if res.masks is not None:
                        # Precisaria alinhar a máscara com a caixa, mas para fallback YOLO direto, pode ser None
                        pass

                    results.append({
                        "bbox": [int(x) for x in b],
                        "score": float(s),
                        "category_id": c,
                        "category_name": res.names[c] if hasattr(res, 'names') else str(c),
                        "mask": mask
                    })
        return results

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
                    time.sleep(0.01)  # Avoid busy loop if frame drop
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
