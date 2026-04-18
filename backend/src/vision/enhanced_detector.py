"""
ChikGuard — Enhanced Object Detector v3
========================================
Pipeline de inferência de alta performance para detecção de pintinhos e galinhas
em granjas industriais.

Arquitetura:
  ┌─────────────────────────────────────────────────────────────────┐
  │  SAHITileEngine (nativo, sem dep. externa)                      │
  │  • Grade configurável de fatias (default 640x640, overlap 20%)  │
  │  • ThreadPoolExecutor (4 workers) — fatias em paralelo          │
  │  • NMS global reagrupando todas as detecções                    │
  ├─────────────────────────────────────────────────────────────────┤
  │  HardwareBackend adaptativo                                     │
  │  • Prioridade: OpenVINO FP16 → ONNX Runtime → PyTorch          │
  ├─────────────────────────────────────────────────────────────────┤
  │  SimpleIoUTracker / ByteTrack (fallback robusto)                │
  └─────────────────────────────────────────────────────────────────┘

Variáveis de ambiente:
  ENABLE_SAHI        = true          (habilita o modo de fatiamento)
  SAHI_SLICE_SIZE    = 640           (lado do tile quadrado em px)
  SAHI_OVERLAP       = 0.20          (sobreposição entre tiles, 0.0–0.5)
  SAHI_WORKERS       = 4             (threads paralelas de inferência)
  SAHI_NMS_IOU       = 0.45          (IoU do NMS global pós-fusão)
  INFERENCE_BACKEND  = openvino      (openvino | onnx | pytorch)
  OPENVINO_MODEL_XML = ""            (caminho para .xml do OpenVINO)
  DETECTION_CONF     = 0.25          (confiança mínima — mais baixa para pintinhos pequenos)
  DETECTION_IOU      = 0.45
  INFERENCE_IMGSZ    = 640
  TRACKER_TYPE       = bytetrack     (bytetrack | botsort)
"""
from __future__ import annotations

import logging
import os
import time
import uuid
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple

import cv2
import numpy as np

# ──────────────────────────────────────────────────────────────────────────────
# Configurações via ENV
# ──────────────────────────────────────────────────────────────────────────────
DETECTION_CONF      = float(os.getenv("DETECTION_CONF",    "0.25"))
DETECTION_IOU       = float(os.getenv("DETECTION_IOU",     "0.45"))
INFERENCE_IMGSZ     = int(os.getenv("INFERENCE_IMGSZ",     "640"))
TRACKER_TYPE        = os.getenv("TRACKER_TYPE",            "bytetrack").strip().lower()
TRACKER_CONFIG      = "botsort.yaml" if TRACKER_TYPE == "botsort" else "bytetrack.yaml"

ENABLE_SAHI         = os.getenv("ENABLE_SAHI",             "true").strip().lower() in ("true", "1", "yes")
SAHI_SLICE_SIZE     = int(os.getenv("SAHI_SLICE_SIZE",     "640"))
SAHI_OVERLAP        = float(os.getenv("SAHI_OVERLAP",      "0.20"))
SAHI_WORKERS        = int(os.getenv("SAHI_WORKERS",        "4"))
SAHI_NMS_IOU        = float(os.getenv("SAHI_NMS_IOU",      "0.45"))

INFERENCE_BACKEND   = os.getenv("INFERENCE_BACKEND",       "pytorch").strip().lower()
OPENVINO_MODEL_XML  = os.getenv("OPENVINO_MODEL_XML",      "").strip()

LOGGER = logging.getLogger("chikguard.cv.enhanced_detector")


# ──────────────────────────────────────────────────────────────────────────────
# Funções auxiliares de NMS
# ──────────────────────────────────────────────────────────────────────────────

def _box_area(box: List) -> float:
    x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
    return max(0.0, float(x2 - x1)) * max(0.0, float(y2 - y1))


def _iou(a: List, b: List) -> float:
    """Intersection-over-Union entre dois bounding boxes [x1,y1,x2,y2]."""
    ix1 = max(a[0], b[0])
    iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2])
    iy2 = min(a[3], b[3])
    inter = max(0.0, float(ix2 - ix1)) * max(0.0, float(iy2 - iy1))
    if inter == 0.0:
        return 0.0
    union = _box_area(a) + _box_area(b) - inter
    return inter / max(union, 1e-6)


def _nms_detections(detections: List[Dict], iou_thresh: float = 0.45) -> List[Dict]:
    """
    Non-Maximum Suppression sobre lista de detecções.
    Mantém a detecção de maior confiança quando IoU entre dois boxes >= iou_thresh.
    """
    if not detections:
        return []

    # Ordena por confiança decrescente
    dets = sorted(detections, key=lambda d: float(d.get("confidence", 0.0)), reverse=True)
    kept = []
    suppressed = [False] * len(dets)

    for i, det_i in enumerate(dets):
        if suppressed[i]:
            continue
        kept.append(det_i)
        box_i = list(det_i["box"])
        for j in range(i + 1, len(dets)):
            if suppressed[j]:
                continue
            box_j = list(dets[j]["box"])
            # Só suprimir se mesma classe (evitar suprimir pintinho por galinha)
            if det_i.get("class_id") != dets[j].get("class_id"):
                continue
            if _iou(box_i, box_j) >= iou_thresh:
                suppressed[j] = True

    return kept


# ──────────────────────────────────────────────────────────────────────────────
# SimpleIoUTracker — Fallback leve para SAHI (ByteTrack nativo funciona apenas
# com inferência YOLO direta via model.track())
# ──────────────────────────────────────────────────────────────────────────────

class SimpleIoUTracker:
    """Rastreador baseado em IoU — usado quando SAHI está ativo."""

    def __init__(self, max_lost: int = 15, iou_threshold: float = 0.25):
        self.next_id       = 1
        self.tracks: Dict  = {}
        self.max_lost      = max_lost
        self.iou_threshold = iou_threshold

    def update(self, boxes: List) -> List[int]:
        """
        Recebe lista de [x1,y1,x2,y2] e retorna lista de track_ids correspondentes.
        """
        if not boxes:
            for tid in list(self.tracks.keys()):
                self.tracks[tid]["lost"] += 1
                if self.tracks[tid]["lost"] > self.max_lost:
                    del self.tracks[tid]
            return []

        track_ids_list = list(self.tracks.keys())
        if not track_ids_list:
            ids = []
            for b in boxes:
                self.tracks[self.next_id] = {"box": b, "lost": 0}
                ids.append(self.next_id)
                self.next_id += 1
            return ids

        track_boxes = [self.tracks[t]["box"] for t in track_ids_list]
        ious = np.zeros((len(boxes), len(track_boxes)), dtype=np.float32)
        for i, b in enumerate(boxes):
            for j, t in enumerate(track_boxes):
                ious[i, j] = _iou(list(b), list(t))

        assigned = [-1] * len(boxes)
        unassigned_dets   = list(range(len(boxes)))
        unassigned_tracks = list(range(len(track_boxes)))

        while unassigned_dets and unassigned_tracks:
            max_iou = np.max(ious)
            if max_iou < self.iou_threshold:
                break
            di, ti = np.unravel_index(np.argmax(ious), ious.shape)
            if di in unassigned_dets and ti in unassigned_tracks:
                tid = track_ids_list[ti]
                assigned[di] = tid
                self.tracks[tid]["box"]  = boxes[di]
                self.tracks[tid]["lost"] = 0
                unassigned_dets.remove(di)
                unassigned_tracks.remove(ti)
            ious[di, :] = -1
            ious[:, ti] = -1

        for ti in unassigned_tracks:
            tid = track_ids_list[ti]
            self.tracks[tid]["lost"] += 1
            if self.tracks[tid]["lost"] > self.max_lost:
                del self.tracks[tid]

        for di in unassigned_dets:
            self.tracks[self.next_id] = {"box": boxes[di], "lost": 0}
            assigned[di] = self.next_id
            self.next_id += 1

        return assigned


# ──────────────────────────────────────────────────────────────────────────────
# SAHITileEngine — Motor de Fatiamento Nativo
# ──────────────────────────────────────────────────────────────────────────────

class SAHITileEngine:
    """
    Divide o frame em tiles sobrepostos e executa inferência em paralelo.

    Para 1080p (1920×1080) com slice_size=640 e overlap=0.20:
      stride_x = 640 * 0.80 = 512 → ~4 colunas
      stride_y = 640 * 0.80 = 512 → ~2 linhas
      Total de tiles ≈ 8 (processo gerenciado por 4 workers)

    O resultado é combinado com NMS global para eliminar detecções duplicadas
    nas bordas sobrepostas entre tiles.
    """

    def __init__(
        self,
        slice_size: int = 640,
        overlap: float = 0.20,
        n_workers: int = 4,
        nms_iou: float = 0.45,
        conf_threshold: float = 0.25,
    ):
        self.slice_size    = slice_size
        self.overlap       = max(0.0, min(overlap, 0.49))
        self.n_workers     = max(1, n_workers)
        self.nms_iou       = nms_iou
        self.conf_threshold = conf_threshold
        self._executor     = ThreadPoolExecutor(max_workers=self.n_workers,
                                                thread_name_prefix="sahi-worker")
        LOGGER.info(
            "[SAHI] Engine inicializado: slice=%dpx overlap=%.0f%% workers=%d nms_iou=%.2f",
            slice_size, overlap * 100, n_workers, nms_iou
        )

    def _compute_tiles(self, h: int, w: int) -> List[Tuple[int, int, int, int]]:
        """
        Calcula as coordenadas (x1, y1, x2, y2) de cada tile no frame completo.
        Garante que o tile final sempre cobre a borda do frame.
        """
        stride = int(self.slice_size * (1.0 - self.overlap))
        stride = max(1, stride)

        tiles = []
        y = 0
        while y < h:
            x = 0
            while x < w:
                x2 = min(x + self.slice_size, w)
                y2 = min(y + self.slice_size, h)
                # Garante que o tile tenha ao menos slice_size em ambas as dimensões
                # ancorando no canto inferior-direito se necessário
                x1 = max(0, x2 - self.slice_size)
                y1 = max(0, y2 - self.slice_size)
                tiles.append((x1, y1, x2, y2))
                if x2 == w:
                    break
                x += stride
            if y2 == h:
                break
            y += stride

        return tiles

    def _infer_tile(
        self,
        tile_img: np.ndarray,
        offset_x: int,
        offset_y: int,
        infer_fn,          # callable: (frame_np) → list[dict]
    ) -> List[Dict]:
        """Executa inferência em um único tile e translada as coordenadas."""
        try:
            raw_dets = infer_fn(tile_img)
        except Exception as exc:
            LOGGER.warning("[SAHI] Falha em tile (ox=%d oy=%d): %s", offset_x, offset_y, exc)
            return []

        translated = []
        for det in raw_dets:
            box = list(det.get("box", [0, 0, 0, 0]))
            if len(box) < 4:
                continue
            # Translada coordenadas do espaço do tile para o espaço do frame completo
            det_out = dict(det)
            det_out["box"] = [
                box[0] + offset_x,
                box[1] + offset_y,
                box[2] + offset_x,
                box[3] + offset_y,
            ]
            translated.append(det_out)
        return translated

    def infer(self, frame: np.ndarray, infer_fn) -> List[Dict]:
        """
        Inferência fatiada assíncrona sobre o frame completo.

        Args:
            frame    : frame BGR (np.ndarray)
            infer_fn : função que aceita um frame recortado e devolve list[dict]
                       com chaves: box, class_id, confidence, track_id, mask_area_px

        Returns:
            Lista de detecções no espaço de coordenadas do frame completo,
            já pós-NMS global.
        """
        h, w = frame.shape[:2]
        tiles = self._compute_tiles(h, w)
        n_tiles = len(tiles)

        LOGGER.debug("[SAHI] Frame %dx%d → %d tiles", w, h, n_tiles)

        futures = {}
        for (x1, y1, x2, y2) in tiles:
            tile_crop = frame[y1:y2, x1:x2]
            future = self._executor.submit(
                self._infer_tile, tile_crop, x1, y1, infer_fn
            )
            futures[future] = (x1, y1)

        all_dets: List[Dict] = []
        for future in as_completed(futures):
            try:
                dets = future.result(timeout=5.0)
                all_dets.extend(dets)
            except Exception as exc:
                LOGGER.warning("[SAHI] Tile future exception: %s", exc)

        # NMS global para eliminar duplicatas nas bordas sobrepostas
        final = _nms_detections(all_dets, iou_thresh=self.nms_iou)

        LOGGER.debug(
            "[SAHI] %d detecções brutas → %d após NMS global",
            len(all_dets), len(final)
        )
        return final

    def shutdown(self):
        """Encerra o ThreadPoolExecutor de forma limpa."""
        self._executor.shutdown(wait=False)


# ──────────────────────────────────────────────────────────────────────────────
# Backend Adaptativo: OpenVINO → ONNX Runtime → PyTorch
# ──────────────────────────────────────────────────────────────────────────────

class _OpenVINOBackend:
    """
    Executa inferência via OpenVINO Runtime (Intel CPU/iGPU).
    Suporta modelos exportados com `yolo.export(format='openvino')`.
    """

    def __init__(self, xml_path: str, conf: float = 0.25, imgsz: int = 640):
        from openvino.runtime import Core  # type: ignore
        self._conf  = conf
        self._imgsz = imgsz

        ie = Core()
        # Tenta GPU integrada primeiro, cai para CPU
        device = "GPU" if "GPU" in ie.available_devices else "CPU"
        model  = ie.read_model(xml_path)
        self._compiled = ie.compile_model(model, device)
        self._input_key  = self._compiled.input(0)
        self._output_key = self._compiled.output(0)
        LOGGER.info("[OpenVINO] Modelo carregado em '%s' (device=%s)", xml_path, device)

    def predict(self, frame: np.ndarray) -> List[Dict]:
        """Pré-processa, executa e pós-processa para o formato padrão de detecções."""
        h_orig, w_orig = frame.shape[:2]
        blob = self._preprocess(frame)
        result = self._compiled({self._input_key: blob})[self._output_key]
        return self._postprocess(result, w_orig, h_orig)

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        img = cv2.resize(frame, (self._imgsz, self._imgsz))
        img = img[:, :, ::-1].astype(np.float32) / 255.0  # BGR→RGB, normalize
        img = np.transpose(img, (2, 0, 1))                 # HWC → CHW
        return np.expand_dims(img, 0)                       # add batch dim

    def _postprocess(self, output: np.ndarray, w_orig: int, h_orig: int) -> List[Dict]:
        """
        Interpreta a saída do modelo YOLOv8 exportado para OpenVINO.
        Formato: [batch, num_det, 4+1+num_classes] ou [batch, 4+num_classes, num_anchors]
        """
        out = np.squeeze(output)  # Remove dimensão de batch

        # YOLOv8 ONNX/OpenVINO export: shape (8400, 4+nc) ou (4+nc, 8400)
        if out.ndim == 2:
            if out.shape[0] < out.shape[1]:
                out = out.T  # Transpõe para (num_anchors, 4+nc)

            # Extrai boxes e scores
            boxes_cxcywh = out[:, :4]
            scores = out[:, 4:]  # (num_anchors, nc)

            class_ids = np.argmax(scores, axis=1)
            confs = scores[np.arange(len(scores)), class_ids]

            # Filtra por confiança
            mask = confs >= self._conf
            boxes_cxcywh = boxes_cxcywh[mask]
            class_ids    = class_ids[mask]
            confs        = confs[mask]

            # Converter cx,cy,w,h → x1,y1,x2,y2 (normalizado → pixels originais)
            dets = []
            scale_x = w_orig / self._imgsz
            scale_y = h_orig / self._imgsz
            for i in range(len(boxes_cxcywh)):
                cx, cy, bw, bh = boxes_cxcywh[i]
                x1 = int((cx - bw / 2) * scale_x)
                y1 = int((cy - bh / 2) * scale_y)
                x2 = int((cx + bw / 2) * scale_x)
                y2 = int((cy + bh / 2) * scale_y)
                dets.append({
                    "box":         [x1, y1, x2, y2],
                    "class_id":    int(class_ids[i]),
                    "confidence":  float(confs[i]),
                    "track_id":    -1,
                    "mask_area_px": 0.0,
                })
            return dets

        LOGGER.warning("[OpenVINO] Formato de saída inesperado: %s", out.shape)
        return []


class _ONNXBackend:
    """Executa inferência via ONNX Runtime (CPU, AVX-512 otimizado)."""

    def __init__(self, onnx_path: str, conf: float = 0.25, imgsz: int = 640):
        import onnxruntime as ort  # type: ignore
        self._conf  = conf
        self._imgsz = imgsz
        providers = ["CPUExecutionProvider"]
        self._session = ort.InferenceSession(onnx_path, providers=providers)
        self._input_name = self._session.get_inputs()[0].name
        LOGGER.info("[ONNX] Modelo carregado: %s", onnx_path)

    def predict(self, frame: np.ndarray) -> List[Dict]:
        h_orig, w_orig = frame.shape[:2]
        blob = self._preprocess(frame)
        output = self._session.run(None, {self._input_name: blob})[0]
        return self._postprocess(output, w_orig, h_orig)

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        img = cv2.resize(frame, (self._imgsz, self._imgsz))
        img = img[:, :, ::-1].astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        return np.expand_dims(img, 0)

    def _postprocess(self, output: np.ndarray, w_orig: int, h_orig: int) -> List[Dict]:
        out = np.squeeze(output)
        if out.ndim == 2:
            if out.shape[0] < out.shape[1]:
                out = out.T
            boxes_cxcywh = out[:, :4]
            scores = out[:, 4:]
            class_ids = np.argmax(scores, axis=1)
            confs = scores[np.arange(len(scores)), class_ids]
            mask = confs >= self._conf
            boxes_cxcywh = boxes_cxcywh[mask]
            class_ids    = class_ids[mask]
            confs        = confs[mask]
            scale_x = w_orig / self._imgsz
            scale_y = h_orig / self._imgsz
            dets = []
            for i in range(len(boxes_cxcywh)):
                cx, cy, bw, bh = boxes_cxcywh[i]
                x1 = int((cx - bw / 2) * scale_x)
                y1 = int((cy - bh / 2) * scale_y)
                x2 = int((cx + bw / 2) * scale_x)
                y2 = int((cy + bh / 2) * scale_y)
                dets.append({
                    "box":         [x1, y1, x2, y2],
                    "class_id":    int(class_ids[i]),
                    "confidence":  float(confs[i]),
                    "track_id":    -1,
                    "mask_area_px": 0.0,
                })
            return dets
        return []


# ──────────────────────────────────────────────────────────────────────────────
# EnhancedObjectDetector — Fachada principal
# ──────────────────────────────────────────────────────────────────────────────

class EnhancedObjectDetector:
    """
    Detector de alta performance com:
      • Backend adaptativo (OpenVINO → ONNX → PyTorch)
      • SAHITileEngine para detecção de objetos pequenos (ativo por padrão)
      • ByteTrack nativo do Ultralytics para modo direto
      • SimpleIoUTracker para modo SAHI (compatível com qualquer backend)
    """

    def __init__(self, model_path: str = "yolov8n-seg.pt"):
        self.yolo_loaded            = False
        self.model                  = None       # Ultralytics YOLO (modo direto)
        self.supports_segmentation  = False
        self._hw_backend            = None       # OpenVINO ou ONNX backend
        self._hw_backend_name       = "none"
        self._sahi:  Optional[SAHITileEngine] = None
        self._tracker               = SimpleIoUTracker(max_lost=18, iou_threshold=0.22)

        # ── Carrega backend de hardware (OpenVINO ou ONNX) ────────────────
        self._init_hardware_backend(model_path)

        # ── Carrega PyTorch/Ultralytics como fallback ou se hw falhou ─────
        if self._hw_backend is None:
            self._init_ultralytics(model_path)

        # ── Inicializa SAHI se habilitado ──────────────────────────────────
        if ENABLE_SAHI and (self._hw_backend is not None or self.yolo_loaded):
            self._sahi = SAHITileEngine(
                slice_size=SAHI_SLICE_SIZE,
                overlap=SAHI_OVERLAP,
                n_workers=SAHI_WORKERS,
                nms_iou=SAHI_NMS_IOU,
                conf_threshold=DETECTION_CONF,
            )
            LOGGER.info(
                "[Detector] SAHI ativado — slice=%dpx overlap=%.0f%% workers=%d",
                SAHI_SLICE_SIZE, SAHI_OVERLAP * 100, SAHI_WORKERS
            )
        else:
            LOGGER.info("[Detector] Modo direto (SAHI desabilitado)")

    # ── Inicialização ──────────────────────────────────────────────────────

    def _init_hardware_backend(self, model_path: str):
        """Tenta carregar OpenVINO (xml) ou ONNX, nessa ordem de prioridade."""

        requested = INFERENCE_BACKEND.lower()

        # 1. OpenVINO — por caminho explícito ou derivado do model_path
        if requested in ("openvino", "auto"):
            xml_path = OPENVINO_MODEL_XML
            if not xml_path:
                # Tenta encontrar o .xml ao lado do modelo
                candidate = model_path.replace(".pt", "_openvino_model")
                xml_candidate = os.path.join(candidate, "model.xml")
                if os.path.exists(xml_candidate):
                    xml_path = xml_candidate

            if xml_path and os.path.exists(xml_path):
                try:
                    self._hw_backend = _OpenVINOBackend(
                        xml_path, conf=DETECTION_CONF, imgsz=INFERENCE_IMGSZ
                    )
                    self._hw_backend_name = "openvino"
                    LOGGER.info("[Detector] Backend: OpenVINO ✓ (%s)", xml_path)
                    return
                except Exception as exc:
                    LOGGER.warning("[Detector] OpenVINO falhou: %s — tentando ONNX", exc)

        # 2. ONNX Runtime
        if requested in ("onnx", "openvino", "auto"):
            onnx_path = model_path.replace(".pt", ".onnx")
            if not os.path.exists(onnx_path):
                onnx_path = os.path.join(os.path.dirname(model_path),
                                         os.path.basename(model_path).replace(".pt", ".onnx"))
            if os.path.exists(onnx_path):
                try:
                    self._hw_backend = _ONNXBackend(
                        onnx_path, conf=DETECTION_CONF, imgsz=INFERENCE_IMGSZ
                    )
                    self._hw_backend_name = "onnx"
                    LOGGER.info("[Detector] Backend: ONNX Runtime ✓ (%s)", onnx_path)
                    return
                except Exception as exc:
                    LOGGER.warning("[Detector] ONNX Runtime falhou: %s — usando PyTorch", exc)

    def _init_ultralytics(self, model_path: str):
        """Carrega o modelo via Ultralytics YOLO (PyTorch)."""
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.yolo_loaded = True
            LOGGER.info("[Detector] Backend: PyTorch/Ultralytics ✓ (%s)", model_path)
            # Warm-up
            self.model.predict(np.zeros((64, 64, 3), dtype=np.uint8), verbose=False)
            # Verifica se suporta segmentação
            dummy = self.model.predict(np.zeros((256, 256, 3), dtype=np.uint8), verbose=False)
            self.supports_segmentation = bool(
                dummy and getattr(dummy[0], "masks", None) is not None
            )
        except Exception as exc:
            LOGGER.exception("[Detector] Erro ao carregar Ultralytics: %s", exc)

    # ── API Pública ──────────────────────────────────────────────────────────

    @property
    def backend_name(self) -> str:
        return self._hw_backend_name if self._hw_backend else (
            "pytorch" if self.yolo_loaded else "none"
        )

    @property
    def sahi_enabled(self) -> bool:
        return self._sahi is not None

    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        Ponto de entrada principal.
        Retorna lista de dicts com: box, class_id, confidence, track_id, mask_area_px.
        """
        if frame is None or frame.size == 0:
            return []

        if self._sahi is not None:
            return self._detect_sahi(frame)
        return self._detect_direct(frame)

    # ── Modo SAHI ────────────────────────────────────────────────────────────

    def _detect_sahi(self, frame: np.ndarray) -> List[Dict]:
        """Inferência via SAHITileEngine com backend adaptativo."""

        def _infer_fn(tile: np.ndarray) -> List[Dict]:
            if self._hw_backend is not None:
                return self._hw_backend.predict(tile)
            # Fallback: Ultralytics predict (sem track — SAHI usa SimpleIoUTracker)
            if self.yolo_loaded and self.model is not None:
                results = self.model.predict(
                    tile,
                    verbose=False,
                    conf=DETECTION_CONF,
                    iou=DETECTION_IOU,
                    imgsz=INFERENCE_IMGSZ,
                )
                return self._parse_ultralytics_result(results[0])
            return []

        detections = self._sahi.infer(frame, _infer_fn)

        # Rastreamento com SimpleIoUTracker
        boxes = [d["box"] for d in detections]
        track_ids = self._tracker.update(boxes)
        for i, tid in enumerate(track_ids):
            detections[i]["track_id"] = int(tid)

        return detections

    # ── Modo Direto (ByteTrack nativo) ───────────────────────────────────────

    def _detect_direct(self, frame: np.ndarray) -> List[Dict]:
        """Inferência direta com ByteTrack integrado (modo legado)."""
        if self._hw_backend is not None:
            # Hardware backend não suporta ByteTrack nativo — usa IoU tracker
            dets = self._hw_backend.predict(frame)
            boxes = [d["box"] for d in dets]
            ids = self._tracker.update(boxes)
            for i, tid in enumerate(ids):
                dets[i]["track_id"] = int(tid)
            return dets

        if not self.yolo_loaded or self.model is None:
            return []

        results = self.model.track(
            frame,
            verbose=False,
            persist=True,
            tracker=TRACKER_CONFIG,
            conf=DETECTION_CONF,
            iou=DETECTION_IOU,
            imgsz=INFERENCE_IMGSZ,
        )
        return self._parse_ultralytics_result(results[0], with_track=True)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_ultralytics_result(result, with_track: bool = False) -> List[Dict]:
        """Converte resultado Ultralytics para formato padrão ChikGuard."""
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return []

        xyxy       = boxes.xyxy.cpu().numpy().astype(int)
        class_ids  = boxes.cls.cpu().numpy().astype(int)
        confidences = boxes.conf.cpu().numpy()

        if with_track and boxes.id is not None:
            track_ids = boxes.id.cpu().numpy().astype(int)
        else:
            track_ids = np.full(len(xyxy), -1, dtype=int)

        mask_areas = np.zeros(len(xyxy), dtype=np.float32)
        masks_obj = getattr(result, "masks", None)
        if masks_obj is not None:
            mask_data = getattr(masks_obj, "data", None)
            if mask_data is not None:
                try:
                    stack = mask_data.cpu().numpy()
                    for i in range(min(len(stack), len(mask_areas))):
                        mask_areas[i] = float(np.sum(stack[i] > 0.5))
                except Exception:
                    pass

        dets = []
        for i in range(len(xyxy)):
            dets.append({
                "box":          list(xyxy[i]),
                "class_id":     int(class_ids[i]),
                "confidence":   float(confidences[i]),
                "track_id":     int(track_ids[i]) if i < len(track_ids) else -1,
                "mask_area_px": float(mask_areas[i]),
            })
        return dets

    def __del__(self):
        try:
            if self._sahi:
                self._sahi.shutdown()
        except Exception:
            pass
