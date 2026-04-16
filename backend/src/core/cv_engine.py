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

import cv2
import math
import queue
import threading
import time
import logging
from collections import deque
from typing import Optional, Dict, Any, List, Tuple

import numpy as np

logger = logging.getLogger("chikguard.cv_engine")

# ─────────────────────────────────────────────────────────────────────────────
# Constantes de classificação visual
# ─────────────────────────────────────────────────────────────────────────────

# Pintinho (1–14 dias): amarelo-palha, muito pequeno
CHICK_HSV_LOW  = np.array([15,  60, 100], dtype=np.uint8)
CHICK_HSV_HIGH = np.array([38, 255, 255], dtype=np.uint8)

# Galinha adulta: branco, pardo, castanho, preto
HEN_HSV_RANGES = [
    (np.array([0,   0, 160], dtype=np.uint8), np.array([180, 40, 255], dtype=np.uint8)),  # branca
    (np.array([10, 30,  60], dtype=np.uint8), np.array([30, 200, 200], dtype=np.uint8)),  # parda/castanha
    (np.array([0,   0,   0], dtype=np.uint8), np.array([180,  80,  60], dtype=np.uint8)), # preta
]

# Limites de área para espécie (fração da área do frame)
CHICK_MAX_AREA_RATIO = 0.010   # pintinho: pequeno
HEN_MIN_AREA_RATIO   = 0.008   # galinha: médio/grande (overlap intencional para casos intermediários)

# Aspect ratio para postura
POSE_LYING_THRESHOLD    = 1.45  # w/h > 1.45 → deitada de lado
POSE_STANDING_THRESHOLD = 0.75  # w/h < 0.75 → em pé / vertical
POSE_PRONE_AREA_RATIO   = 0.60  # área/bbox < 60% e imóvel → prostrada (só com máscara seg)

# Cores de visualização (BGR)
COLOR_CHICK   = (0,   220, 255)  # amarelo-ciano
COLOR_HEN     = (0,   200,   0)  # verde
COLOR_BIRD    = (255, 200,   0)  # azul-ciano (genérico)
COLOR_CARCASS = (0,     0, 180)  # vermelho escuro
COLOR_INFO    = (200, 200, 200)  # cinza claro para HUD

FONT        = cv2.FONT_HERSHEY_SIMPLEX
FONT_SMALL  = cv2.FONT_HERSHEY_PLAIN
FONT_SCALE  = 0.48
LINE_WIDTH  = 2

# ─────────────────────────────────────────────────────────────────────────────
# Análise de Postura da Ave
# ─────────────────────────────────────────────────────────────────────────────

class BirdPoseAnalyzer:
    """
    Determina a posição/postura de uma ave a partir da bounding box
    e, opcionalmente, da máscara de segmentação.
    """

    @staticmethod
    def analyze(box: List[int], mask_area_px: float = 0.0,
                frame_shape: Tuple[int, ...] = (480, 640, 3)) -> Dict[str, Any]:
        """
        Retorna dicionário com:
          pose        : 'standing' | 'lying' | 'prone' | 'unknown'
          pose_label  : texto em PT para overlay
          pose_angle  : ângulo estimado em graus (0 = vertical, 90 = horizontal)
          aspect_ratio: w/h
        """
        x1, y1, x2, y2 = [int(v) for v in box]
        w  = max(1, x2 - x1)
        h  = max(1, y2 - y1)
        ar = w / h

        # Ângulo a partir do aspect ratio (mapeado 0–90°)
        angle = math.degrees(math.atan2(w, h))

        if ar > POSE_LYING_THRESHOLD:
            pose       = "lying"
            pose_label = "→ DEITADA"
        elif ar < POSE_STANDING_THRESHOLD:
            pose       = "standing"
            pose_label = "↑ EM PÉ"
        else:
            pose       = "unknown"
            pose_label = "● NORMAL"

        # Refinamento por máscara de segmentação (quando disponível)
        if mask_area_px > 0:
            bbox_area = max(1.0, float(w * h))
            fill_ratio = mask_area_px / bbox_area
            if fill_ratio < POSE_PRONE_AREA_RATIO and pose == "unknown":
                pose       = "prone"
                pose_label = "⚠ PROSTRADA"

        return {
            "pose":         pose,
            "pose_label":   pose_label,
            "pose_angle":   round(angle, 1),
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
        self._batch_age_day: int = 30    # padrão: assume lote adulto
        self._lock = threading.Lock()

    def set_batch_age(self, age_day: int):
        with self._lock:
            self._batch_age_day = max(1, int(age_day))

    def classify(self, frame: np.ndarray, box: List[int],
                 class_name: str = "bird", mask_area_px: float = 0.0) -> Dict[str, Any]:
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

        species      = "bird"
        species_label = "AVE"
        color        = COLOR_BIRD

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
                    chick_ratio = float(np.sum(chick_mask > 0)) / max(1, roi.shape[0] * roi.shape[1])

                    # Verifica padrões de galinha
                    hen_ratio = 0.0
                    for lo, hi in HEN_HSV_RANGES:
                        m = cv2.inRange(hsv, lo, hi)
                        hen_ratio = max(hen_ratio, float(np.sum(m > 0)) / max(1, roi.shape[0] * roi.shape[1]))

                    if chick_ratio > 0.30:
                        color_vote = "chick"
                    elif hen_ratio > 0.35:
                        color_vote = "hen"
                except Exception:
                    pass

        # ── Fusão dos votos ────────────────────────────────────────────────
        votes_chick = sum([
            1 if size_vote  == "chick" else 0,
            1 if color_vote == "chick" else 0,
            1 if age_chick_prior else 0,
        ])
        votes_hen = sum([
            1 if size_vote  == "hen" else 0,
            1 if color_vote == "hen" else 0,
            1 if not age_chick_prior else 0,
        ])

        if votes_chick >= 2:
            species       = "chick"
            species_label = "PINTINHO"
            color         = COLOR_CHICK
        elif votes_hen >= 2:
            species       = "hen"
            species_label = "GALINHA"
            color         = COLOR_HEN
        else:
            # Tiebreak: usar age_prior
            if age_chick_prior:
                species       = "chick"
                species_label = "PINTINHO"
                color         = COLOR_CHICK
            else:
                species       = "hen"
                species_label = "GALINHA"
                color         = COLOR_HEN

        return {
            "species":       species,
            "species_label": species_label,
            "color":         color,
            "age_prior":     age_chick_prior,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Métricas de Performance
# ─────────────────────────────────────────────────────────────────────────────

class PerfMetrics:
    """Coleta FPS e latência de componentes individuais do pipeline."""

    def __init__(self, window: int = 30):
        self._lock            = threading.Lock()
        self._cap_times:  deque   = deque(maxlen=window)
        self._inf_times:  deque   = deque(maxlen=window)
        self._inf_lat_ms: deque   = deque(maxlen=window)

    def tick_capture(self):
        with self._lock:
            self._cap_times.append(time.perf_counter())

    def tick_inference(self, latency_ms: float):
        with self._lock:
            self._inf_times.append(time.perf_counter())
            self._inf_lat_ms.append(latency_ms)

    def get(self) -> Dict[str, float]:
        with self._lock:
            def fps(ts: deque) -> float:
                if len(ts) < 2:
                    return 0.0
                elapsed = ts[-1] - ts[0]
                return round((len(ts) - 1) / max(1e-6, elapsed), 1)

            lat = round(float(np.mean(self._inf_lat_ms)) if self._inf_lat_ms else 0.0, 1)
            return {
                "fps_camera":    fps(self._cap_times),
                "fps_inference": fps(self._inf_times),
                "latency_ms":    lat,
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

    def __init__(self, camera_index: int, target_fps: float = 60.0,
                 width: int = 1280, height: int = 720,
                 backend: int = cv2.CAP_DSHOW, metrics: Optional[PerfMetrics] = None):
        self.camera_index  = camera_index
        self.target_fps    = max(1.0, target_fps)
        self.width         = width
        self.height        = height
        self.backend       = backend
        self.metrics       = metrics

        self._frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self._lock         = threading.Lock()
        self._cap: Optional[cv2.VideoCapture] = None
        self._running      = False
        self._thread: Optional[threading.Thread] = None
        self._is_live      = False  # False = usando simulação/vídeo
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
        self._thread  = threading.Thread(target=self._run, daemon=True, name="cv-capture")
        self._thread.start()
        logger.info("[CameraCapture] Thread iniciada. Camera=%d target_fps=%.0f", self.camera_index, self.target_fps)

    def stop(self):
        self._running = False
        if self._cap:
            self._cap.release()

    # ── Loop interno ───────────────────────────────────────────────────────

    def _open_camera(self) -> bool:
        try:
            cap = cv2.VideoCapture(self.camera_index, self.backend)
            if not cap.isOpened():
                cap.release()
                return False
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS,          self.target_fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)
            # MJPEG codec: menor overhead de decodificação, mais FPS
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            with self._lock:
                if self._cap:
                    self._cap.release()
                self._cap    = cap
                self._is_live = True
            logger.info("[CameraCapture] Câmera aberta: %.0fx%.0f @ %.0f FPS",
                        cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                        cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
                        cap.get(cv2.CAP_PROP_FPS))
            return True
        except Exception as exc:
            logger.warning("[CameraCapture] Falha ao abrir câmera: %s", exc)
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
                        logger.warning("[CameraCapture] Câmera perdida após %d falhas.", self._consecutive_failures)
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

    def __init__(self,
                 detector,                     # ObjectDetector do app.py
                 species_classifier: SpeciesClassifier,
                 pose_analyzer: BirdPoseAnalyzer,
                 metrics: PerfMetrics,
                 imgsz: int = 480,
                 class_name_fn=None):          # função id → nome da classe
        self._detector          = detector
        self._species           = species_classifier
        self._pose              = pose_analyzer
        self._metrics           = metrics
        self._imgsz             = imgsz
        self._class_name_fn     = class_name_fn or (lambda cid: "bird")

        self._in_queue:  queue.Queue = queue.Queue(maxsize=2)
        self._out_queue: queue.Queue = queue.Queue(maxsize=2)

        self._running   = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._run, daemon=True, name="cv-inference")
        self._thread.start()
        logger.info("[InferencePipeline] Thread de inferência iniciada. imgsz=%d", self._imgsz)

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

                raw_dets = self._detector.detect(frame) # _detector is configured in app.py, assume model.track is handled there or here if updated.
                detections = self._enrich(frame, raw_dets)

                lat_ms = (time.perf_counter() - t0) * 1000.0
                self._metrics.tick_inference(lat_ms)

                # Deposita resultado (descarta antigo se cheio)
                if self._out_queue.full():
                    try:
                        self._out_queue.get_nowait()
                    except queue.Empty:
                        pass
                self._out_queue.put_nowait({
                    "detections":  detections,
                    "latency_ms":  round(lat_ms, 1),
                    "frame_shape": frame.shape,
                })
            except queue.Empty:
                continue
            except Exception as exc:
                logger.exception("[InferencePipeline] Erro de inferência: %s", exc)

    def _enrich(self, frame: np.ndarray, raw: list) -> list:
        """Adiciona espécie e postura a cada detecção bruta do YOLO."""
        enriched = []
        for det in raw:
            box       = det.get("box", [0, 0, 1, 1])
            cid       = int(det.get("class_id", 0))
            cname     = self._class_name_fn(cid)
            mask_area = float(det.get("mask_area_px", 0.0))

            pose_info    = self._pose.analyze(box, mask_area, frame.shape)
            species_info = self._species.classify(frame, box, cname, mask_area)

            det_out = dict(det)
            det_out.update(pose_info)
            det_out.update(species_info)
            enriched.append(det_out)
        return enriched


# ─────────────────────────────────────────────────────────────────────────────
# Overlay Visual Rico
# ─────────────────────────────────────────────────────────────────────────────

class CVOverlay:
    """
    Desenha no frame anotações profissionais:
    - Bounding box colorida por espécie
    - Label: espécie + postura + ID + confiança
    - HUD: FPS câmera | FPS inferência | Latência | Contagens
    - Indicador de modo (pintinho/galinha)
    """

    @staticmethod
    def draw_detections(frame: np.ndarray, detections: list,
                        carcass_uids: set,
                        class_name_fn=None) -> np.ndarray:
        """Desenha todas as detecções enriquecidas no frame."""
        draw = frame
        h, w = draw.shape[:2]

        for det in detections:
            box   = det.get("box", [0, 0, 1, 1])
            x1, y1, x2, y2 = [int(v) for v in box]

            uid         = int(det.get("stable_bird_uid", det.get("track_id", -1)))
            conf        = float(det.get("confidence", 0.0))
            species_lbl = det.get("species_label", "AVE")
            pose_lbl    = det.get("pose_label", "")
            color       = det.get("color", COLOR_BIRD)
            is_carcass  = uid in carcass_uids

            if is_carcass:
                color       = COLOR_CARCASS
                species_lbl = "POSSÍVEL CÁRCAÇA"
                pose_lbl    = ""

            # Bounding box
            cv2.rectangle(draw, (x1, y1), (x2, y2), color, LINE_WIDTH)

            # Label principal: espécie + ID
            id_str   = f"#{uid}" if uid >= 0 else ""
            main_lbl = f"{species_lbl} {id_str} {conf:.0%}"
            _put_label(draw, main_lbl, (x1, y1 - 6), color)

            # Sub-label: postura (apenas se relevante)
            if pose_lbl and pose_lbl != "● NORMAL":
                _put_label(draw, pose_lbl, (x1, y2 + 14), color, scale=0.42)

        return draw

    @staticmethod
    def draw_hud(frame: np.ndarray, metrics: Dict[str, float],
                 counts: Dict[str, int], behavior_status: str,
                 mode: str = "aves") -> np.ndarray:
        """Desenha o HUD de performance e contagem no canto do frame."""
        h, w = frame.shape[:2]
        fps_cam  = metrics.get("fps_camera",    0.0)
        fps_inf  = metrics.get("fps_inference", 0.0)
        lat_ms   = metrics.get("latency_ms",    0.0)
        total    = counts.get("total",   0)
        chicks   = counts.get("chicks",  0)
        hens     = counts.get("hens",    0)

        # Painel semi-transparente no topo-esquerdo
        overlay  = frame.copy()
        ph, pw   = 105, 340
        cv2.rectangle(overlay, (0, 0), (pw, ph), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        lines = [
            (f"📷 CAM {fps_cam:.0f} FPS  |  🧠 INF {fps_inf:.0f} FPS  |  ⏱ {lat_ms:.0f} ms",
             (8, 18), 0.46, (180, 255, 100)),
            (f"🐣 Pintinhos: {chicks}   🐔 Galinhas: {hens}   TOTAL: {total}",
             (8, 38), 0.46, (255, 220, 80)),
            (f"Comportamento: {behavior_status}",
             (8, 58), 0.42, (80, 200, 255)),
        ]

        for text, pos, scale, clr in lines:
            # Fallback ASCII para evitar crash com emoji em fonts padrão
            text_safe = _strip_emoji(text)
            cv2.putText(frame, text_safe, pos, FONT, scale, clr, 1, cv2.LINE_AA)

        return frame


def _put_label(img: np.ndarray, text: str, pos: Tuple[int, int],
               color, scale: float = FONT_SCALE):
    """Desenha label com sombra para legibilidade em qualquer fundo."""
    x, y = pos
    h, w = img.shape[:2]
    x = max(2, min(x, w - 5))
    y = max(14, min(y, h - 2))
    text = _strip_emoji(text)
    # Sombra preta
    cv2.putText(img, text, (x + 1, y + 1), FONT, scale, (0, 0, 0),       2, cv2.LINE_AA)
    # Texto colorido
    cv2.putText(img, text, (x,     y    ), FONT, scale, color,            1, cv2.LINE_AA)


def _strip_emoji(text: str) -> str:
    """Remove emoji e caracteres não-ASCII que o OpenCV não renderiza."""
    import re
    return re.sub(r'[^\x00-\x7F]+', '', text)


# ─────────────────────────────────────────────────────────────────────────────
# Contagem de Espécies
# ─────────────────────────────────────────────────────────────────────────────

def count_by_species(live_birds: dict, detections: list, now: float,
                     bird_live_ttl: float) -> Dict[str, int]:
    """
    Retorna dict com contagens de pintinhos, galinhas e total
    a partir das detecções enriquecidas da iteração atual.
    """
    chicks = 0
    hens   = 0
    for det in detections:
        sp = det.get("species", "bird")
        if sp == "chick":
            chicks += 1
        elif sp == "hen":
            hens += 1
        else:
            hens += 1  # conta genérico como galinha para não subestimar

    total = sum(
        1 for info in live_birds.values()
        if (now - float(info["last_seen"])) <= bird_live_ttl
    )

    return {"chicks": chicks, "hens": hens, "total": total}
