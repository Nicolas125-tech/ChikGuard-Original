"""
ChikGuard -- InferenceEngine v2 (ONNX-First, Frame-Skipping)
=============================================================
Motor de inferencia de alta performance com:

  1. Frame Skipping controlado: inferencia corre a max INFERENCE_FPS (default 15).
     Frames intermediarios sao descartados para poupar CPU sem travar o stream.

  2. Backend adaptativo (prioridade):
       ONNX Runtime (CUDAExecutionProvider se disponivel, senao CPU AVX-512)
       -> OpenVINO (Intel iGPU/CPU)
       -> PyTorch/Ultralytics (fallback)

  3. Pre-processamento otimizado:
       - Resize com INTER_LINEAR (mais rapido que INTER_CUBIC)
       - BGR->RGB com slice (sem copia)
       - FP32 pre-alocado no buffer

  4. Pos-processamento vetorizado (NumPy puro, sem loops Python).

Exportar modelo YOLO para ONNX com FP16:
  # FP32 (compativel com qualquer hardware):
  yolo export model=yolov8n.pt format=onnx opset=17 simplify=True imgsz=640

  # FP16 (recomendado para GPU NVIDIA):
  yolo export model=yolov8n.pt format=onnx opset=17 simplify=True imgsz=640 half=True

  # TensorRT (maximo desempenho NVIDIA):
  yolo export model=yolov8n.pt format=engine imgsz=640 half=True device=0
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("chikguard.inference")

# ─────────────────────────────────────────────────────────────────────────────
# Configuracao via ENV
# ─────────────────────────────────────────────────────────────────────────────
DETECTION_CONF = float(os.getenv("DETECTION_CONF", "0.25"))
DETECTION_IOU = float(os.getenv("DETECTION_IOU", "0.45"))
INFERENCE_IMGSZ = int(os.getenv("INFERENCE_IMGSZ", "640"))
INFERENCE_FPS = float(os.getenv("INFERENCE_FPS", "15.0"))  # max FPS de inferencia
INFERENCE_BACKEND = os.getenv("INFERENCE_BACKEND", "onnx").strip().lower()
OPENVINO_XML = os.getenv("OPENVINO_MODEL_XML", "").strip()
TRACKER_TYPE = os.getenv("TRACKER_TYPE", "bytetrack").strip().lower()
TRACKER_CONFIG = "botsort.yaml" if TRACKER_TYPE == "botsort" else "bytetrack.yaml"


# ─────────────────────────────────────────────────────────────────────────────
# NMS vetorizado (NumPy puro, sem loops Python internos)
# ─────────────────────────────────────────────────────────────────────────────


def _nms_numpy(boxes: np.ndarray, scores: np.ndarray, iou_thresh: float) -> np.ndarray:
    """
    Non-Maximum Suppression vetorizado.
    boxes  : (N, 4) float32 [x1, y1, x2, y2]
    scores : (N,)   float32
    Retorna indices dos boxes mantidos.
    """
    if len(boxes) == 0:
        return np.array([], dtype=np.int32)

    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    order = scores.argsort()[::-1]

    keep = []
    while len(order) > 0:
        i = order[0]
        keep.append(i)
        if len(order) == 1:
            break
        rest = order[1:]
        ix1 = np.maximum(x1[i], x1[rest])
        iy1 = np.maximum(y1[i], y1[rest])
        ix2 = np.minimum(x2[i], x2[rest])
        iy2 = np.minimum(y2[i], y2[rest])
        inter = np.maximum(0.0, ix2 - ix1) * np.maximum(0.0, iy2 - iy1)
        iou = inter / np.maximum(areas[i] + areas[rest] - inter, 1e-6)
        order = rest[iou < iou_thresh]

    return np.array(keep, dtype=np.int32)


# ─────────────────────────────────────────────────────────────────────────────
# Pre-processamento otimizado
# ─────────────────────────────────────────────────────────────────────────────


def _preprocess(frame: np.ndarray, imgsz: int) -> Tuple[np.ndarray, float, float]:
    """
    Prepara o frame para inferencia ONNX.

    Retorna:
        blob     : (1, 3, imgsz, imgsz) float32 normalizado [0,1]
        scale_x  : fator de escala x (frame_w / imgsz)
        scale_y  : fator de escala y (frame_h / imgsz)
    """
    h, w = frame.shape[:2]
    # INTER_LINEAR e o mais rapido com boa qualidade
    resized = cv2.resize(frame, (imgsz, imgsz), interpolation=cv2.INTER_LINEAR)
    # BGR->RGB sem copia extra (slice reverso no eixo do canal)
    rgb = resized[:, :, ::-1]
    # CHW, float32, normalizado -- astype faz copia, mas e necessaria
    blob = (rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[np.newaxis]
    return blob, w / imgsz, h / imgsz


def _postprocess(
    output: np.ndarray,
    scale_x: float,
    scale_y: float,
    conf_thresh: float,
    iou_thresh: float,
) -> List[Dict[str, Any]]:
    """
    Pos-processamento vetorizado para saida YOLO ONNX.
    Suporta shape (1, 4+nc, 8400) — padrao YOLOv8/v10.
    """
    out = np.squeeze(output)  # (4+nc, 8400) ou (8400, 4+nc)
    if out.ndim != 2:
        return []
    if out.shape[0] < out.shape[1]:
        out = out.T  # normaliza para (8400, 4+nc)

    boxes_cxcywh = out[:, :4]
    scores_mat = out[:, 4:]  # (8400, nc)
    class_ids = np.argmax(scores_mat, axis=1)
    confs = scores_mat[np.arange(len(scores_mat)), class_ids]

    # Filtragem por confianca (vetorizada)
    mask = confs >= conf_thresh
    if not np.any(mask):
        return []

    boxes_cxcywh = boxes_cxcywh[mask]
    class_ids = class_ids[mask]
    confs = confs[mask]

    # cx,cy,w,h -> x1,y1,x2,y2
    cx, cy, bw, bh = boxes_cxcywh.T
    x1 = (cx - bw / 2) * scale_x
    y1 = (cy - bh / 2) * scale_y
    x2 = (cx + bw / 2) * scale_x
    y2 = (cy + bh / 2) * scale_y
    xyxy = np.stack([x1, y1, x2, y2], axis=1)

    # NMS por classe
    keep_indices = []
    for cid in np.unique(class_ids):
        cls_mask = class_ids == cid
        idx = np.where(cls_mask)[0]
        kept = _nms_numpy(xyxy[idx], confs[idx], iou_thresh)
        keep_indices.extend(idx[kept].tolist())

    dets = []
    for i in keep_indices:
        dets.append(
            {
                "box": [int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i])],
                "class_id": int(class_ids[i]),
                "confidence": float(confs[i]),
                "track_id": -1,
                "mask_area_px": 0.0,
            }
        )
    return dets


# ─────────────────────────────────────────────────────────────────────────────
# Backends
# ─────────────────────────────────────────────────────────────────────────────


class _ONNXBackend:
    """
    ONNX Runtime com suporte a CUDA (se disponivel) e CPU AVX-512.
    Ordem de providers: CUDAExecutionProvider -> CPUExecutionProvider
    """

    def __init__(self, onnx_path: str, conf: float, imgsz: int):
        import onnxruntime as ort  # type: ignore

        self._conf = conf
        self._imgsz = imgsz

        # Tenta CUDA primeiro, cai para CPU
        available = ort.get_available_providers()
        if "CUDAExecutionProvider" in available:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            logger.info("[ONNX] Usando CUDA ExecutionProvider")
        else:
            providers = ["CPUExecutionProvider"]
            logger.info("[ONNX] Usando CPU ExecutionProvider (AVX otimizado)")

        sess_opts = ort.SessionOptions()
        sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_opts.intra_op_num_threads = max(1, (os.cpu_count() or 4) // 2)

        self._session = ort.InferenceSession(onnx_path, sess_opts, providers=providers)
        self._input_name = self._session.get_inputs()[0].name

        # Warm-up (compila kernels)
        dummy = np.zeros((1, 3, imgsz, imgsz), dtype=np.float32)
        self._session.run(None, {self._input_name: dummy})
        logger.info("[ONNX] Sessao pronta: %s", onnx_path)

    def infer(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        blob, sx, sy = _preprocess(frame, self._imgsz)
        output = self._session.run(None, {self._input_name: blob})[0]
        return _postprocess(output, sx, sy, self._conf, DETECTION_IOU)


class _OpenVINOBackend:
    """OpenVINO Runtime (Intel CPU/iGPU, prioritiza GPU integrada)."""

    def __init__(self, xml_path: str, conf: float, imgsz: int):
        from openvino.runtime import Core  # type: ignore

        self._conf = conf
        self._imgsz = imgsz

        ie = Core()
        device = "GPU" if "GPU" in ie.available_devices else "CPU"
        model = ie.read_model(xml_path)
        self._compiled = ie.compile_model(model, device)
        self._input_key = self._compiled.input(0)
        self._output_key = self._compiled.output(0)

        # Warm-up
        dummy = np.zeros((1, 3, imgsz, imgsz), dtype=np.float32)
        self._compiled({self._input_key: dummy})
        logger.info("[OpenVINO] Modelo em '%s' no device=%s", xml_path, device)

    def infer(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        blob, sx, sy = _preprocess(frame, self._imgsz)
        output = self._compiled({self._input_key: blob})[self._output_key]
        return _postprocess(output, sx, sy, self._conf, DETECTION_IOU)


class _UltralyticsBackend:
    """Fallback PyTorch/Ultralytics com ByteTrack integrado."""

    def __init__(self, model_path: str, conf: float, imgsz: int):
        from ultralytics import YOLO  # type: ignore

        self._conf = conf
        self._imgsz = imgsz
        self._model = YOLO(model_path)
        # Warm-up
        self._model.predict(np.zeros((64, 64, 3), dtype=np.uint8), verbose=False)
        self._supports_seg = False
        try:
            res = self._model.predict(np.zeros((128, 128, 3), dtype=np.uint8), verbose=False)
            self._supports_seg = getattr(res[0], "masks", None) is not None
        except Exception:
            pass
        logger.info("[PyTorch] Ultralytics YOLO carregado: %s", model_path)

    def infer(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        results = self._model.track(
            frame,
            verbose=False,
            persist=True,
            tracker=TRACKER_CONFIG,
            conf=self._conf,
            iou=DETECTION_IOU,
            imgsz=self._imgsz,
        )
        return _parse_ultralytics(results[0])


def _parse_ultralytics(result) -> List[Dict[str, Any]]:
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    xyxy = boxes.xyxy.cpu().numpy().astype(int)
    class_ids = boxes.cls.cpu().numpy().astype(int)
    confs = boxes.conf.cpu().numpy()
    track_ids = (
        boxes.id.cpu().numpy().astype(int)
        if boxes.id is not None
        else np.full(len(xyxy), -1, dtype=int)
    )

    mask_areas = np.zeros(len(xyxy), dtype=np.float32)
    masks_obj = getattr(result, "masks", None)
    if masks_obj is not None:
        data = getattr(masks_obj, "data", None)
        if data is not None:
            try:
                stack = data.cpu().numpy()
                for i in range(min(len(stack), len(mask_areas))):
                    mask_areas[i] = float(np.sum(stack[i] > 0.5))
            except Exception:
                pass

    dets = []
    for i in range(len(xyxy)):
        dets.append(
            {
                "box": list(xyxy[i]),
                "class_id": int(class_ids[i]),
                "confidence": float(confs[i]),
                "track_id": int(track_ids[i]),
                "mask_area_px": float(mask_areas[i]),
            }
        )
    return dets


# ─────────────────────────────────────────────────────────────────────────────
# InferenceEngine — fachada com frame-skipping
# ─────────────────────────────────────────────────────────────────────────────


class InferenceEngine:
    """
    Motor de inferencia de alta performance.

    Frame Skipping:
        .should_infer() retorna True somente quando o intervalo minimo
        (1 / INFERENCE_FPS) passou desde a ultima inferencia.
        Chame .last_detections para reusar o resultado do ultimo frame.

    Uso tipico no camera_loop:
        engine = InferenceEngine(model_path)
        while True:
            frame = cam.read()
            if frame is None:
                continue
            if engine.should_infer():
                dets = engine.infer(frame)
            else:
                dets = engine.last_detections   # reutiliza resultado anterior
            # ... desenha overlay com dets ...
    """

    def __init__(self, model_path: str):
        self._backend: Any = None
        self._backend_name: str = "none"
        self.last_detections: List[Dict] = []
        self._last_infer_t: float = 0.0
        self._min_interval: float = 1.0 / max(1.0, INFERENCE_FPS)

        self._load_backend(model_path)

    # ── Carregamento adaptativo ───────────────────────────────────────────────

    def _load_backend(self, model_path: str):
        """Tenta backends na ordem: ONNX -> OpenVINO -> PyTorch."""

        # 1. ONNX Runtime
        if INFERENCE_BACKEND in ("onnx", "auto", "pytorch"):
            onnx_path = model_path.replace(".pt", ".onnx")
            if os.path.exists(onnx_path):
                try:
                    self._backend = _ONNXBackend(onnx_path, DETECTION_CONF, INFERENCE_IMGSZ)
                    self._backend_name = "onnx"
                    logger.info("[Engine] Backend ativo: ONNX Runtime (%s)", onnx_path)
                    return
                except Exception as e:
                    logger.warning("[Engine] ONNX falhou: %s", e)

        # 2. OpenVINO
        if INFERENCE_BACKEND in ("openvino", "auto"):
            xml_path = OPENVINO_XML
            if not xml_path:
                candidate = model_path.replace(".pt", "_openvino_model/model.xml")
                if os.path.exists(candidate):
                    xml_path = candidate

            if xml_path and os.path.exists(xml_path):
                try:
                    self._backend = _OpenVINOBackend(xml_path, DETECTION_CONF, INFERENCE_IMGSZ)
                    self._backend_name = "openvino"
                    logger.info("[Engine] Backend ativo: OpenVINO (%s)", xml_path)
                    return
                except Exception as e:
                    logger.warning("[Engine] OpenVINO falhou: %s", e)

        # 3. PyTorch/Ultralytics (fallback)
        try:
            self._backend = _UltralyticsBackend(model_path, DETECTION_CONF, INFERENCE_IMGSZ)
            self._backend_name = "pytorch"
            logger.info("[Engine] Backend ativo: PyTorch/Ultralytics")
        except Exception as e:
            logger.error("[Engine] Todos os backends falharam: %s", e)

    # ── API publica ───────────────────────────────────────────────────────────

    @property
    def backend_name(self) -> str:
        return self._backend_name

    @property
    def is_ready(self) -> bool:
        return self._backend is not None

    def should_infer(self) -> bool:
        """
        Controle de frame-skipping baseado em tempo.
        Retorna True no maximo INFERENCE_FPS vezes por segundo.
        """
        return (time.perf_counter() - self._last_infer_t) >= self._min_interval

    def infer(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Executa inferencia no frame e atualiza last_detections.
        Chame somente se should_infer() == True para economizar CPU.
        """
        if not self.is_ready or frame is None or frame.size == 0:
            return self.last_detections

        t0 = time.perf_counter()
        dets = self._backend.infer(frame)
        lat = (time.perf_counter() - t0) * 1000.0

        self._last_infer_t = time.perf_counter()
        self.last_detections = dets

        logger.debug("[Engine] %d deteccoes em %.1f ms", len(dets), lat)
        return dets

    def force_infer(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Inferencia sem checagem de frame-skip (para warmup / debug)."""
        self._last_infer_t = 0.0  # reseta o timer
        return self.infer(frame)
