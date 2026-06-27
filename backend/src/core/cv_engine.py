"""
ChikGuard CV Engine v2 — Motor de Visão Computacional Profissional
=================================================================
Pipeline desacoplado: Captura de câmera ↔ Inferência YOLO em threads separadas.
- Detecção de pintinhos e galinhas em qualquer posição
- Classificação visual por espécie (pintinho/galinha/ave)
- Análise de postura (em pé, deitada, prostrada)
- FPS máximo da câmera, independente da velocidade de inferência
- Métricas de performance em tempo real (FPS câmera, FPS inferência, latência ms)
"""

from __future__ import annotations

import logging
import math
import queue
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("chikguard.cv_engine")

_track_history = {}
_MAX_HISTORY = 45

# ─────────────────────────────────────────────────────────────────────────────
# Constantes de classificação visual
# ─────────────────────────────────────────────────────────────────────────────

# Pintinho (1–14 dias): amarelo-palha, muito pequeno
CHICK_HSV_LOW = np.array([15, 60, 100], dtype=np.uint8)
CHICK_HSV_HIGH = np.array([38, 255, 255], dtype=np.uint8)

# Galinha adulta: branco, pardo, castanho, preto
HEN_HSV_RANGES = [
    (np.array([0, 0, 160], dtype=np.uint8), np.array([180, 40, 255], dtype=np.uint8)),  # branca
    (
        np.array([10, 30, 60], dtype=np.uint8),
        np.array([30, 200, 200], dtype=np.uint8),
    ),  # parda/castanha
    (np.array([0, 0, 0], dtype=np.uint8), np.array([180, 80, 60], dtype=np.uint8)),  # preta
]

# Limites de área para espécie (fração da área do frame)
CHICK_MAX_AREA_RATIO = 0.010  # pintinho: pequeno
HEN_MIN_AREA_RATIO = 0.008  # galinha: médio/grande (overlap intencional para casos intermediários)

# Aspect ratio para postura
POSE_LYING_THRESHOLD = 1.45  # w/h > 1.45 → deitada de lado
POSE_STANDING_THRESHOLD = 0.75  # w/h < 0.75 → em pé / vertical
POSE_PRONE_AREA_RATIO = 0.60  # área/bbox < 60% e imóvel → prostrada (só com máscara seg)

# Cores de visualização (BGR)
COLOR_CHICK = (0, 220, 255)  # amarelo-ciano
COLOR_HEN = (0, 200, 0)  # verde
COLOR_BIRD = (255, 200, 0)  # azul-ciano (genérico)
COLOR_CARCASS = (0, 0, 180)  # vermelho escuro
COLOR_INFO = (200, 200, 200)  # cinza claro para HUD

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SMALL = cv2.FONT_HERSHEY_PLAIN
FONT_SCALE = 0.48
LINE_WIDTH = 2

# ─────────────────────────────────────────────────────────────────────────────
# Análise de Postura da Ave
# ─────────────────────────────────────────────────────────────────────────────


class BirdPoseAnalyzer:
    """
    Determina a posição/postura de uma ave a partir da bounding box
    e, opcionalmente, da máscara de segmentação.
    """

    @staticmethod
    def analyze(
        box: List[int], mask_area_px: float = 0.0, frame_shape: Tuple[int, ...] = (480, 640, 3)
    ) -> Dict[str, Any]:
        """
        Retorna dicionário com:
          pose        : 'standing' | 'lying' | 'prone' | 'unknown'
          pose_label  : texto em PT para overlay
          pose_angle  : ângulo estimado em graus (0 = vertical, 90 = horizontal)
          aspect_ratio: w/h
        """
        x1, y1, x2, y2 = [int(v) for v in box]
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)
        ar = w / h

        # Ângulo a partir do aspect ratio (mapeado 0–90°)
        angle = math.degrees(math.atan2(w, h))

        if ar > POSE_LYING_THRESHOLD:
            pose = "lying"
            pose_label = "→ DEITADA"
        elif ar < POSE_STANDING_THRESHOLD:
            pose = "standing"
            pose_label = "↑ EM PÉ"
        else:
            pose = "unknown"
            pose_label = "● NORMAL"

        # Refinamento por máscara de segmentação (quando disponível)
        if mask_area_px > 0:
            bbox_area = max(1.0, float(w * h))
            fill_ratio = mask_area_px / bbox_area
            if fill_ratio < POSE_PRONE_AREA_RATIO and pose == "unknown":
                pose = "prone"
                pose_label = "⚠ PROSTRADA"

        return {
            "pose": pose,
            "pose_label": pose_label,
            "pose_angle": round(angle, 1),
            "aspect_ratio": round(ar, 3),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Classificador de Espécie (Pintinho vs Galinha)
# ─────────────────────────────────────────────────────────────────────────────


class SpeciesClassifier:
    """
    Classifica cada detecção como 'chick' (pintinho), 'hen' (galinha) ou 'bird' (genérico).
    Utiliza cor HSV da ROI + tamanho relativo ao frame + idade do lote como prior.
    """

    def __init__(self):
        self._batch_age_day: int = 30  # padrão: assume lote adulto
        self._lock = threading.Lock()

    def set_batch_age(self, age_day: int):
        with self._lock:
            self._batch_age_day = max(1, int(age_day))

    def classify(
        self, frame: np.ndarray, box: List[int], class_name: str = "bird", mask_area_px: float = 0.0
    ) -> Dict[str, Any]:
        """
        Retorna dict:
          species      : 'chick' | 'hen' | 'bird'
          species_label: texto em PT
          color        : cor BGR para overlay
          age_prior    : bool — lote jovem sugere pintinhos
        """
        x1, y1, x2, y2 = [int(v) for v in box]
        fh, fw = frame.shape[:2]
        frame_area = max(1, fh * fw)

        # Clampar ROI aos limites do frame
        rx1 = max(0, min(x1, fw - 1))
        ry1 = max(0, min(y1, fh - 1))
        rx2 = max(0, min(x2, fw))
        ry2 = max(0, min(y2, fh))

        with self._lock:
            age = self._batch_age_day

        bbox_area = max(1, (rx2 - rx1) * (ry2 - ry1))
        area_ratio = bbox_area / frame_area

        # Prior de idade: ≤ 14 dias → maioritariamente pintinhos
        age_chick_prior = age <= 14

        species = "bird"
        species_label = "AVE"
        color = COLOR_BIRD

        # ── Classificação por tamanho ──────────────────────────────────────
        if area_ratio < CHICK_MAX_AREA_RATIO:
            size_vote = "chick"
        elif area_ratio > HEN_MIN_AREA_RATIO:
            size_vote = "hen"
        else:
            size_vote = "unknown"

        # ── Classificação por cor HSV da ROI ──────────────────────────────
        color_vote = "unknown"
        if rx2 > rx1 and ry2 > ry1:
            roi = frame[ry1:ry2, rx1:rx2]
            if roi.size > 0:
                try:
                    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    # Verifica amarelo-palha (pintinho)
                    chick_mask = cv2.inRange(hsv, CHICK_HSV_LOW, CHICK_HSV_HIGH)
                    chick_ratio = float(np.sum(chick_mask > 0)) / max(
                        1, roi.shape[0] * roi.shape[1]
                    )

                    # Verifica padrões de galinha
                    hen_ratio = 0.0
                    for lo, hi in HEN_HSV_RANGES:
                        m = cv2.inRange(hsv, lo, hi)
                        hen_ratio = max(
                            hen_ratio, float(np.sum(m > 0)) / max(1, roi.shape[0] * roi.shape[1])
                        )

                    if chick_ratio > 0.30:
                        color_vote = "chick"
                    elif hen_ratio > 0.35:
                        color_vote = "hen"
                except Exception:
                    pass

        # ── Fusão dos votos ────────────────────────────────────────────────
        votes_chick = sum(
            [
                1 if size_vote == "chick" else 0,
                1 if color_vote == "chick" else 0,
                1 if age_chick_prior else 0,
            ]
        )
        votes_hen = sum(
            [
                1 if size_vote == "hen" else 0,
                1 if color_vote == "hen" else 0,
                1 if not age_chick_prior else 0,
            ]
        )

        if votes_chick >= 2:
            species = "chick"
            species_label = "PINTINHO"
            color = COLOR_CHICK
        elif votes_hen >= 2:
            species = "hen"
            species_label = "GALINHA"
            color = COLOR_HEN
        else:
            # Tiebreak: usar age_prior
            if age_chick_prior:
                species = "chick"
                species_label = "PINTINHO"
                color = COLOR_CHICK
            else:
                species = "hen"
                species_label = "GALINHA"
                color = COLOR_HEN

        return {
            "species": species,
            "species_label": species_label,
            "color": color,
            "age_prior": age_chick_prior,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Métricas de Performance
# ─────────────────────────────────────────────────────────────────────────────


class PerfMetrics:
    """Coleta FPS, latência e métricas SAHI de componentes do pipeline."""

    def __init__(self, window: int = 30):
        self._lock = threading.Lock()
        self._cap_times: deque = deque(maxlen=window)
        self._inf_times: deque = deque(maxlen=window)
        self._inf_lat_ms: deque = deque(maxlen=window)
        # Métricas específicas do SAHI
        self._sahi_tiles: deque = deque(maxlen=window)  # tiles por frame
        self._sahi_enabled: bool = False
        self._backend_name: str = "pytorch"

    def tick_capture(self):
        with self._lock:
            self._cap_times.append(time.perf_counter())

    def tick_inference(self, latency_ms: float, sahi_tiles: int = 0):
        with self._lock:
            self._inf_times.append(time.perf_counter())
            self._inf_lat_ms.append(latency_ms)
            if sahi_tiles > 0:
                self._sahi_tiles.append(sahi_tiles)
                self._sahi_enabled = True

    def set_backend(self, name: str):
        """Registra o nome do backend de inferência para exibição no HUD."""
        with self._lock:
            self._backend_name = name

    def get(self) -> Dict[str, Any]:
        with self._lock:

            def fps(ts: deque) -> float:
                if len(ts) < 2:
                    return 0.0
                elapsed = ts[-1] - ts[0]
                return round((len(ts) - 1) / max(1e-6, elapsed), 1)

            lat = round(float(np.mean(self._inf_lat_ms)) if self._inf_lat_ms else 0.0, 1)
            avg_tiles = round(float(np.mean(self._sahi_tiles)) if self._sahi_tiles else 0.0, 1)
            return {
                "fps_camera": fps(self._cap_times),
                "fps_inference": fps(self._inf_times),
                "latency_ms": lat,
                "sahi_enabled": self._sahi_enabled,
                "sahi_avg_tiles": avg_tiles,
                "backend_name": self._backend_name,
            }


# ─────────────────────────────────────────────────────────────────────────────
# Thread de Captura (Camera Reader Thread)
# ─────────────────────────────────────────────────────────────────────────────


class CameraCapture:
    """
    Thread dedicada à leitura de frames da câmera em velocidade máxima.
    Deposita frames numa fila pequena (maxsize=2) — o consumidor sempre
    obtém o frame mais recente, descartando frames intermediários.
    """

    def __init__(
        self,
        camera_index: int,
        target_fps: float = 60.0,
        width: int = 1280,
        height: int = 720,
        backend: int = cv2.CAP_DSHOW,
        metrics: Optional[PerfMetrics] = None,
    ):
        self.camera_index = camera_index
        self.target_fps = max(1.0, target_fps)
        self.width = width
        self.height = height
        self.backend = backend
        self.metrics = metrics

        self._frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self._lock = threading.Lock()
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._is_live = False  # False = usando simulação/vídeo
        self._consecutive_failures = 0
        self._last_reconnect = 0.0

    # ── Propriedades públicas ──────────────────────────────────────────────

    @property
    def is_live(self) -> bool:
        return self._is_live

    def latest_frame(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """Retorna o frame mais recente ou None se não disponível."""
        try:
            return self._frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    # ── Controle ──────────────────────────────────────────────────────────

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="cv-capture")
        self._thread.start()
        logger.info(
            "[CameraCapture] Thread iniciada. Camera=%d target_fps=%.0f",
            self.camera_index,
            self.target_fps,
        )

    def stop(self):
        self._running = False
        if self._cap:
            self._cap.release()

    # ── Loop interno ───────────────────────────────────────────────────────

    def _open_camera(self) -> bool:
        backends_to_try = [self.backend, cv2.CAP_ANY]
        if self.backend == cv2.CAP_ANY:
            backends_to_try = [cv2.CAP_ANY]

        for b in backends_to_try:
            try:
                cap = cv2.VideoCapture(self.camera_index, b)
                if not cap.isOpened():
                    cap.release()
                    continue

                # Try to set resolution but don't fail if it doesn't stick
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                # Check if we can actually read a frame
                ret, _ = cap.read()
                if not ret:
                    cap.release()
                    continue

                with self._lock:
                    if self._cap:
                        self._cap.release()
                    self._cap = cap
                    self._is_live = True

                backend_name = (
                    "DSHOW" if b == cv2.CAP_DSHOW else "MSMF" if b == cv2.CAP_MSMF else "ANY"
                )
                logger.info(
                    "[CameraCapture] Câmera aberta (%s): Index=%d Res=%.0fx%.0f @ %.0f FPS",
                    backend_name,
                    self.camera_index,
                    cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                    cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
                    cap.get(cv2.CAP_PROP_FPS),
                )
                return True
            except Exception as exc:
                logger.warning("[CameraCapture] Falha ao abrir com backend %d: %s", b, exc)
                continue

        logger.error("[CameraCapture] Nenhuma camera real encontrada nos backends testados.")
        return False

    def _run(self):
        if not self._open_camera():
            with self._lock:
                self._is_live = False

        min_interval = 1.0 / self.target_fps

        while self._running:
            t0 = time.perf_counter()
            try:
                with self._lock:
                    cap = self._cap

                if cap is None or not self._is_live:
                    # Tenta reconectar periodicamente
                    now = time.perf_counter()
                    if now - self._last_reconnect > 3.0:
                        self._last_reconnect = now
                        if self._open_camera():
                            self._consecutive_failures = 0
                    time.sleep(0.05)
                    continue

                ret, frame = cap.read()
                if not ret:
                    self._consecutive_failures += 1
                    if self._consecutive_failures > 20:
                        with self._lock:
                            self._is_live = False
                        logger.warning(
                            "[CameraCapture] Câmera perdida após %d falhas.",
                            self._consecutive_failures,
                        )
                    time.sleep(0.02)
                    continue

                self._consecutive_failures = 0
                if self.metrics:
                    self.metrics.tick_capture()

                # Deposita na fila (substitui frame antigo se cheio)
                if self._frame_queue.full():
                    try:
                        self._frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                self._frame_queue.put_nowait(frame)

            except Exception as exc:
                logger.exception("[CameraCapture] Erro inesperado: %s", exc)
                time.sleep(0.1)

            # Throttle mínimo para não queimar CPU em excesso
            elapsed = time.perf_counter() - t0
            sleep_t = min_interval - elapsed
            if sleep_t > 0.001:
                time.sleep(sleep_t)


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline de Inferência
# ─────────────────────────────────────────────────────────────────────────────


class InferencePipeline:
    """
    Recebe frames do CameraCapture (ou de qualquer produtor) e produz
    detecções enriquecidas (espécie + postura) com rastreamento de performance.
    Executa em thread própria para não bloquear a leitura da câmera.
    """

    def __init__(
        self,
        detector,  # ObjectDetector do app.py
        species_classifier: SpeciesClassifier,
        pose_analyzer: BirdPoseAnalyzer,
        metrics: PerfMetrics,
        imgsz: int = 480,
        class_name_fn=None,
    ):  # função id → nome da classe
        self._detector = detector
        self._species = species_classifier
        self._pose = pose_analyzer
        self._metrics = metrics
        self._imgsz = imgsz
        self._class_name_fn = class_name_fn or (lambda cid: "bird")

        self._in_queue: queue.Queue = queue.Queue(maxsize=2)
        self._out_queue: queue.Queue = queue.Queue(maxsize=2)

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self.frame_skip = 5  # Roda a inferência pesada apenas a cada 5 frames

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="cv-inference")
        self._thread.start()
        logger.info("[InferencePipeline] Thread de inferência iniciada. imgsz=%d", self._imgsz)

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def stop(self):
        self._running = False


    def submit_frame(self, frame: np.ndarray):
        """Submete frame para inferência (descarta se fila cheia — mantém latência baixa)."""
        if self._in_queue.full():
            try:
                self._in_queue.get_nowait()
            except queue.Empty:
                pass
        try:
            self._in_queue.put_nowait(frame)
        except queue.Full:
            pass

    def get_result(self, timeout: float = 0.08):
        """Retorna último resultado de inferência ou None."""
        try:
            return self._out_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _run(self):
        while self._running:
            try:
                frame = self._in_queue.get(timeout=0.1)
                t0 = time.perf_counter()

                self._frame_count += 1
                run_heavy = self._frame_count % self.frame_skip == 0

                # Pré-processamento CV: CLAHE (Melhora contraste em baixa luz e poeira)
                try:
                    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
                    l, a, b = cv2.split(lab)
                    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
                    l_clahe = clahe.apply(l)
                    lab_clahe = cv2.merge((l_clahe, a, b))
                    enhanced_frame = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
                except Exception:
                    enhanced_frame = frame

                # Chama o detector com a flag para evitar processamento se for um frame intermediário
                raw_dets = self._detector.detect(enhanced_frame, run_heavy_inference=run_heavy)
                detections = self._enrich(enhanced_frame, raw_dets)

                lat_ms = (time.perf_counter() - t0) * 1000.0
                self._metrics.tick_inference(lat_ms)

                # Deposita resultado (descarta antigo se cheio)
                if self._out_queue.full():
                    try:
                        self._out_queue.get_nowait()
                    except queue.Empty:
                        pass
                self._out_queue.put_nowait(
                    {
                        "detections": detections,
                        "latency_ms": round(lat_ms, 1),
                        "frame_shape": frame.shape,
                    }
                )
            except queue.Empty:
                continue
            except Exception as exc:
                logger.exception("[InferencePipeline] Erro de inferência: %s", exc)

    def _enrich(self, frame: np.ndarray, raw: list) -> list:
        """Adiciona espécie e postura a cada detecção bruta do YOLO."""
        enriched = []
        for det in raw:
            box = det.get("box", [0, 0, 1, 1])
            cid = int(det.get("class_id", 0))
            cname = self._class_name_fn(cid)
            mask_area = float(det.get("mask_area_px", 0.0))

            pose_info = self._pose.analyze(box, mask_area, frame.shape)
            species_info = self._species.classify(frame, box, cname, mask_area)

            det_out = dict(det)
            det_out.update(pose_info)
            det_out.update(species_info)
            enriched.append(det_out)
        return enriched


# ───────────────────────────────────────────────────────────────────────────────
# Overlay Visual Rico -- Premium AI Vision Interface
# ───────────────────────────────────────────────────────────────────────────────


class CVOverlay:
    """
    Overlay visual estilo SOTA AI tracking:
    - Zona de monitoramento: poligono translucido magenta
    - Bounding boxes neon com cantos marcados, ID tag e sombra
    - HUD: painel translucido topo-direito com contadores grandes
    - Tira de FPS/latencia na base
    - Indicador LIVE piscante
    - Branding ChikGuard
    """

    @staticmethod
    def draw_detections(
        frame: np.ndarray, detections: list, carcass_uids: set, class_name_fn=None
    ) -> np.ndarray:
        """Desenha deteccoes enriquecidas com bounding boxes neon + ID tags."""
        draw = frame
        h, w = draw.shape[:2]

        for det in detections:
            box = det.get("box", [0, 0, 1, 1])
            x1, y1, x2, y2 = [int(v) for v in box]

            uid = int(det.get("stable_bird_uid", det.get("track_id", -1)))
            conf = float(det.get("confidence", 0.0))
            species_lbl = det.get("species_label", "AVE")
            pose_lbl = det.get("pose_label", "")
            color = det.get("color", COLOR_BIRD)
            is_carcass = uid in carcass_uids

            if is_carcass:
                color = COLOR_CARCASS
                species_lbl = "CARCACA"
                pose_lbl = ""

            # Neon glow: borda exterior escura + interior brilhante
            cv2.rectangle(draw, (x1 - 1, y1 - 1), (x2 + 1, y2 + 1), (0, 0, 0), 2)
            cv2.rectangle(draw, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

            # Center Crosshair
            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
            cv2.line(draw, (cx - 5, cy), (cx + 5, cy), color, 1, cv2.LINE_AA)
            cv2.line(draw, (cx, cy - 5), (cx, cy + 5), color, 1, cv2.LINE_AA)

            # Motion Trail (Rastro de movimento)
            if uid >= 0:
                if uid not in _track_history:
                    _track_history[uid] = deque(maxlen=_MAX_HISTORY)
                _track_history[uid].append((cx, cy))

                # Desenha o rastro (fading effect seria ideal, mas polyline eh mais rapido)
                pts = np.array(_track_history[uid], dtype=np.int32)
                if len(pts) > 1:
                    cv2.polylines(
                        draw, [pts], isClosed=False, color=color, thickness=2, lineType=cv2.LINE_AA
                    )

            # Cantos marcados estilo targeting
            cr = 8
            tk = 2
            cv2.line(draw, (x1, y1), (x1 + cr, y1), color, tk, cv2.LINE_AA)
            cv2.line(draw, (x1, y1), (x1, y1 + cr), color, tk, cv2.LINE_AA)
            cv2.line(draw, (x2, y1), (x2 - cr, y1), color, tk, cv2.LINE_AA)
            cv2.line(draw, (x2, y1), (x2, y1 + cr), color, tk, cv2.LINE_AA)
            cv2.line(draw, (x1, y2), (x1 + cr, y2), color, tk, cv2.LINE_AA)
            cv2.line(draw, (x1, y2), (x1, y2 - cr), color, tk, cv2.LINE_AA)
            cv2.line(draw, (x2, y2), (x2 - cr, y2), color, tk, cv2.LINE_AA)
            cv2.line(draw, (x2, y2), (x2, y2 - cr), color, tk, cv2.LINE_AA)

            # ID tag com fundo escuro
            id_str = f"#{uid}" if uid >= 0 else "#?"
            (tw, th), _ = cv2.getTextSize(id_str, FONT, 0.40, 1)
            tx, ty = x1, max(y1 - 4, th + 2)
            cv2.rectangle(draw, (tx - 1, ty - th - 2), (tx + tw + 2, ty + 1), (0, 0, 0), -1)
            cv2.putText(draw, id_str, (tx, ty), FONT, 0.40, color, 1, cv2.LINE_AA)

            # Rotulo de especie abaixo da caixa
            sp_tag = f"{species_lbl} {conf:.0%}"
            _put_text_shadow(draw, sp_tag, (x1, y2 + 12), FONT, 0.38, color, 1)

            # Postura (apenas anomalias)
            if pose_lbl and "NORMAL" not in pose_lbl:
                _put_text_shadow(draw, pose_lbl, (x1, y2 + 24), FONT, 0.36, (0, 80, 255), 1)

        # Cleanup memory guard
        if len(_track_history) > 3000:
            _track_history.clear()

        return draw

    @staticmethod
    def draw_hud(
        frame: np.ndarray,
        metrics: Dict[str, Any],
        counts: Dict[str, int],
        behavior_status: str,
        mode: str = "aves",
    ) -> np.ndarray:
        """HUD premium estilo AI tracking -- poligono de zona + contador grande + FPS strip."""
        h, w = frame.shape[:2]
        fps_cam = metrics.get("fps_camera", 0.0)
        fps_inf = metrics.get("fps_inference", 0.0)
        lat_ms = metrics.get("latency_ms", 0.0)
        sahi_on = bool(metrics.get("sahi_enabled", False))
        backend = str(metrics.get("backend_name", "pytorch"))
        total = counts.get("total", 0)
        chicks = counts.get("chicks", 0)
        hens = counts.get("hens", 0)

        overlay = frame.copy()

        # -- 1. Zona de Monitoramento: poligono translucido magenta ----------
        mx = int(w * 0.04)
        my = int(h * 0.08)
        zone_pts = np.array(
            [
                [mx, my],
                [w - mx, my],
                [w - mx, h - my],
                [mx, h - my],
            ],
            dtype=np.int32,
        )
        cv2.fillPoly(overlay, [zone_pts], (180, 0, 180))
        cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)
        cv2.polylines(
            frame, [zone_pts], isClosed=True, color=(255, 0, 255), thickness=2, lineType=cv2.LINE_AA
        )
        _put_text_shadow(
            frame, "ZONA DE MONITORAMENTO", (mx + 6, my - 5), FONT, 0.40, (255, 0, 255), 1
        )

        # -- 2. Painel HUD: topo-direito ------------------------------------
        pw = min(260, w - 20)
        ph = 120
        px1 = w - pw - 8
        py1 = 8
        px2 = w - 8
        py2 = py1 + ph

        panel = frame.copy()
        cv2.rectangle(panel, (px1, py1), (px2, py2), (8, 8, 8), -1)
        cv2.addWeighted(panel, 0.75, frame, 0.25, 0, frame)
        cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 255, 100), 1, cv2.LINE_AA)

        _put_text_shadow(frame, "CHIKGUARD AI", (px1 + 8, py1 + 16), FONT, 0.46, (0, 255, 120), 1)
        cv2.line(frame, (px1 + 8, py1 + 21), (px2 - 8, py1 + 21), (0, 255, 100), 1)

        total_txt = f"TOTAL: {total:,}"
        _put_text_shadow(frame, total_txt, (px1 + 8, py1 + 52), FONT, 0.82, (0, 255, 60), 2)

        _put_text_shadow(
            frame, f"PINTINHOS: {chicks}", (px1 + 8, py1 + 74), FONT, 0.45, (0, 220, 255), 1
        )
        _put_text_shadow(
            frame, f"GALINHAS : {hens}", (px1 + 8, py1 + 91), FONT, 0.45, (0, 200, 100), 1
        )

        beh_clr = (0, 60, 255) if "ANOMALIA" in behavior_status.upper() else (60, 200, 60)
        _put_text_shadow(frame, behavior_status, (px1 + 8, py1 + 110), FONT, 0.38, beh_clr, 1)

        # -- 3. Tira de metricas na parte inferior -------------------------
        strip_bg = frame.copy()
        cv2.rectangle(strip_bg, (0, h - 22), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(strip_bg, 0.60, frame, 0.40, 0, frame)
        sahi_txt = " (SAHI)" if sahi_on else ""
        fps_str = (
            f"CAM {fps_cam:.0f}fps  INF {fps_inf:.0f}fps  "
            f"{lat_ms:.0f}ms  [{backend.upper()}{sahi_txt}]"
        )
        _put_text_shadow(frame, fps_str, (8, h - 8), FONT, 0.38, (160, 160, 255), 1)

        # -- 4. Indicador LIVE piscante ------------------------------------
        if int(time.time() * 2) % 2 == 0:
            cv2.circle(frame, (12, 14), 5, (0, 0, 255), -1, cv2.LINE_AA)
            _put_text_shadow(frame, "LIVE", (22, 20), FONT, 0.44, (30, 30, 255), 1)
        else:
            cv2.circle(frame, (12, 14), 5, (40, 40, 80), -1, cv2.LINE_AA)
            _put_text_shadow(frame, "LIVE", (22, 20), FONT, 0.44, (80, 80, 120), 1)

        return frame


def _put_text_shadow(
    img: np.ndarray, text: str, pos: Tuple[int, int], font, scale: float, color, thickness: int = 1
):
    """Texto com sombra preta para legibilidade em qualquer fundo."""
    x, y = pos
    fh, fw = img.shape[:2]
    x = max(2, min(x, fw - 5))
    y = max(14, min(y, fh - 2))
    text = _strip_emoji(text)
    cv2.putText(img, text, (x + 1, y + 1), font, scale, (0, 0, 0), thickness + 1, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


def _put_label(img: np.ndarray, text: str, pos: Tuple[int, int], color, scale: float = FONT_SCALE):
    """Alias legado para _put_text_shadow com parametros simplificados."""
    _put_text_shadow(img, text, pos, FONT, scale, color, 1)


def _strip_emoji(text: str) -> str:
    """Remove emoji e caracteres nao-ASCII que o OpenCV nao renderiza."""
    import re

    return re.sub(r"[^\x00-\x7F]+", "", text)


# ─────────────────────────────────────────────────────────────────────────────
# Contagem de Espécies
# ─────────────────────────────────────────────────────────────────────────────


def count_by_species(
    live_birds: dict, detections: list, now: float, bird_live_ttl: float
) -> Dict[str, int]:
    """
    Retorna dict com contagens de pintinhos, galinhas e total
    a partir das detecções enriquecidas da iteração atual.
    """
    chicks = 0
    hens = 0
    for det in detections:
        sp = det.get("species", "bird")
        if sp == "chick":
            chicks += 1
        elif sp == "hen":
            hens += 1
        else:
            hens += 1  # conta genérico como galinha para não subestimar

    total = sum(
        1 for info in live_birds.values() if (now - float(info["last_seen"])) <= bird_live_ttl
    )

    return {"chicks": chicks, "hens": hens, "total": total}
