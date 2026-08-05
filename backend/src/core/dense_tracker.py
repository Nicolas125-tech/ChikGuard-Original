"""
ChikGuard -- DenseTracker v1 (ByteTrack-like SOTA)
====================================================
Tracker robusto para alta densidade de objetos visuamente identicos.

Arquitetura:
  - Filtro de Kalman por track (previsao de movimento com velocidade)
  - Associacao em 2 estagios (ByteTrack): alta-confianca -> baixa-confianca
  - IoU puro para associacao (sem Re-ID por aparencia -- pintinhos sao identicos)
  - Estados: TENTATIVO -> CONFIRMADO -> PERDIDO -> REMOVIDO
  - Re-ID por previsao espacial: track reaparece proximo ao ponto previsto pelo Kalman

Parametros via ENV:
  TRACK_HIGH_THRESH   = 0.50   (confianca minima para 1a etapa de associacao)
  TRACK_LOW_THRESH    = 0.10   (confianca minima para 2a etapa ByteTrack)
  NEW_TRACK_THRESH    = 0.60   (confianca minima para criar nova track)
  TRACK_BUFFER        = 30     (frames de tolerancia para tracks perdidas)
  MATCH_THRESH        = 0.85   (limiar de IoU para associacao)
  MAX_TIME_LOST       = 45     (frames antes de remover track definitivamente)
"""


import logging
import os
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger("chikguard.dense_tracker")

# ── Configuracao via ENV ──────────────────────────────────────────────────────
TRACK_HIGH_THRESH = float(os.getenv("TRACK_HIGH_THRESH", "0.50"))
TRACK_LOW_THRESH = float(os.getenv("TRACK_LOW_THRESH", "0.10"))
NEW_TRACK_THRESH = float(os.getenv("NEW_TRACK_THRESH", "0.60"))
TRACK_BUFFER = int(os.getenv("TRACK_BUFFER", "30"))
MATCH_THRESH = float(os.getenv("MATCH_THRESH", "0.85"))
MAX_TIME_LOST = int(os.getenv("MAX_TIME_LOST", "45"))


# =============================================================================
# Filtro de Kalman 1D-por-eixo para bbox (8 estados, 4 medidas)
# Estado: [cx, cy, w, h, vx, vy, vw, vh]
# Medida: [cx, cy, w, h]
# =============================================================================


class KalmanBoxTracker:
    """
    Filtro de Kalman para rastrear uma bounding box no espaco [cx, cy, w, h].

    Estado interno de 8 dimensoes:
      [cx, cy, w, h, vx, vy, vw, vh]

    Permite prever a posicao futura mesmo sem deteccao atual,
    mantendo o track ativo durante oclusao temporaria.
    """

    _count = 0  # Contador global de track IDs

    def __init__(self, bbox: List[float]):
        """
        bbox: [x1, y1, x2, y2]
        """
        KalmanBoxTracker._count += 1
        self.track_id = KalmanBoxTracker._count

        # Matrizes do filtro de Kalman
        dt = 1.0  # delta-tempo (1 frame)

        # Matriz de transicao de estado F (8x8)
        # Modelo de velocidade constante: posicao += velocidade * dt
        self.F = np.eye(8, dtype=np.float64)
        for i in range(4):
            self.F[i, i + 4] = dt

        # Matriz de observacao H (4x8) — observamos apenas cx, cy, w, h
        self.H = np.eye(4, 8, dtype=np.float64)

        # Ruido do processo Q (incerteza do modelo de movimento)
        self.Q = np.diag(
            [
                1e-2,
                1e-2,
                1e-2,
                1e-2,  # posicao
                5e-3,
                5e-3,
                1e-3,
                1e-3,  # velocidade (mais incerta)
            ]
        ).astype(np.float64)

        # Ruido de medicao R (incerteza da deteccao)
        self.R = np.diag([1e-1, 1e-1, 1e-1, 1e-1]).astype(np.float64)

        # Covariancia do estado inicial P
        self.P = np.diag(
            [
                10.0,
                10.0,
                10.0,
                10.0,  # posicao: alta incerteza inicial
                1000.0,
                1000.0,
                1000.0,
                1000.0,  # velocidade: muito incerta
            ]
        ).astype(np.float64)

        # Estado inicial a partir da deteccao
        cx, cy, w, h = self._xyxy_to_cxcywh(bbox)
        self.x = np.array([[cx], [cy], [w], [h], [0.0], [0.0], [0.0], [0.0]], dtype=np.float64)

        # Metadados do track
        self.time_since_update = 0  # frames sem atualizacao
        self.hit_streak = 0  # frames consecutivos com atualizacao
        self.age = 0  # frames de vida total
        self.state = "TENTATIVE"  # TENTATIVE | CONFIRMED | LOST
        self.last_bbox = list(bbox)
        self.confidence = 0.0
        self.class_id = 0

    # ── Kalman: Predict ───────────────────────────────────────────────────────

    def predict(self) -> np.ndarray:
        """Avanca o estado do filtro um passo no tempo (sem medicao)."""
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        self.age += 1
        self.time_since_update += 1
        if self.time_since_update > 0:
            self.hit_streak = 0
        return self._get_bbox()

    # ── Kalman: Update ────────────────────────────────────────────────────────

    def update(self, bbox: List[float], confidence: float = 1.0, class_id: int = 0):
        """Atualiza o filtro com uma nova medicao (deteccao)."""
        z = np.array(self._xyxy_to_cxcywh(bbox), dtype=np.float64).reshape(4, 1)

        # Inovacao y = z - H*x
        y = z - self.H @ self.x

        # Ganho de Kalman K = P*H^T * (H*P*H^T + R)^-1
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)

        # Atualiza estado e covariancia
        self.x = self.x + K @ y
        self.P = (np.eye(8) - K @ self.H) @ self.P

        self.time_since_update = 0
        self.hit_streak += 1
        self.confidence = confidence
        self.class_id = class_id
        self.last_bbox = list(bbox)

        # Promove para CONFIRMED apos N atualizacoes consecutivas
        if self.state == "TENTATIVE" and self.hit_streak >= 3:
            self.state = "CONFIRMED"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_bbox(self) -> List[float]:
        """Retorna bbox prevista em formato [x1, y1, x2, y2]."""
        cx, cy, w, h = self.x[:4].flatten()
        w = max(1.0, abs(w))
        h = max(1.0, abs(h))
        return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]

    def get_predicted_bbox(self) -> List[float]:
        return self._get_bbox()

    def get_centroid(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self._get_bbox()
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    @staticmethod
    def _xyxy_to_cxcywh(bbox: List[float]) -> Tuple[float, float, float, float]:
        x1, y1, x2, y2 = bbox
        return (x1 + x2) / 2, (y1 + y2) / 2, abs(x2 - x1), abs(y2 - y1)

    def __repr__(self):
        return f"Track(id={self.track_id}, state={self.state}, age={self.age}, lost={self.time_since_update})"


# =============================================================================
# Algoritmo de Associacao (Hungarian / Greedy IoU)
# =============================================================================


def _iou_matrix(bboxes_a: List[List[float]], bboxes_b: List[List[float]]) -> np.ndarray:
    """
    Calcula a matriz de IoU entre dois conjuntos de bounding boxes.
    Retorna: (len_a, len_b) matriz float32
    """
    if not bboxes_a or not bboxes_b:
        return np.zeros((len(bboxes_a), len(bboxes_b)), dtype=np.float32)

    a = np.array(bboxes_a, dtype=np.float32)  # (N, 4)
    b = np.array(bboxes_b, dtype=np.float32)  # (M, 4)

    # Areas individuais
    area_a = np.maximum(0, a[:, 2] - a[:, 0]) * np.maximum(0, a[:, 3] - a[:, 1])
    area_b = np.maximum(0, b[:, 2] - b[:, 0]) * np.maximum(0, b[:, 3] - b[:, 1])

    # IoU vetorizado via broadcasting
    ix1 = np.maximum(a[:, 0:1], b[:, 0])
    iy1 = np.maximum(a[:, 1:2], b[:, 1])
    ix2 = np.minimum(a[:, 2:3], b[:, 2])
    iy2 = np.minimum(a[:, 3:4], b[:, 3])
    inter = np.maximum(0, ix2 - ix1) * np.maximum(0, iy2 - iy1)
    union = area_a[:, None] + area_b[None, :] - inter

    return inter / np.maximum(union, 1e-6)


def _greedy_match(
    iou_mat: np.ndarray, thresh: float
) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """
    Associacao gulosa: ordena pares por IoU decrescente e aceita o melhor.
    Mais rapido que Hungarian para alta densidade (O(N*M log(N*M)) vs O(N^3)).

    Retorna: (matches, unmatched_dets, unmatched_tracks)
    """
    if iou_mat.size == 0:
        return [], list(range(iou_mat.shape[0])), list(range(iou_mat.shape[1]))

    # Pares ordenados por IoU decrescente
    pairs = np.dstack(np.unravel_index(np.argsort(-iou_mat.ravel()), iou_mat.shape))[0]

    matched_det = set()
    matched_track = set()
    matches = []

    for det_idx, trk_idx in pairs:
        if iou_mat[det_idx, trk_idx] < thresh:
            break
        if det_idx not in matched_det and trk_idx not in matched_track:
            matches.append((int(det_idx), int(trk_idx)))
            matched_det.add(det_idx)
            matched_track.add(trk_idx)

    n_det = iou_mat.shape[0]
    n_trk = iou_mat.shape[1]
    unmatched_dets = [i for i in range(n_det) if i not in matched_det]
    unmatched_tracks = [j for j in range(n_trk) if j not in matched_track]

    return matches, unmatched_dets, unmatched_tracks


# =============================================================================
# DenseTracker — Orquestrador principal
# =============================================================================


class DenseTracker:
    """
    Tracker SOTA para alta densidade de objetos visualmente identicos.

    Implementa o algoritmo ByteTrack com duas rodadas de associacao:
      1a Rodada: deteccoes de ALTA confianca associadas a tracks confirmadas
      2a Rodada: deteccoes de BAIXA confianca associadas a tracks recentemente perdidas
                 (captura reentradas de aves que ficaram escondidas)

    Nao usa Re-ID por aparencia — pintinhos sao identicos.
    Usa exclusivamente predicao de movimento (Kalman) + IoU espacial.

    Uso:
        tracker = DenseTracker()
        tracked = tracker.update(detections)
        for t in tracked:
            print(t["track_id"], t["bbox"], t["state"])
    """

    def __init__(self):
        self._tracks: List[KalmanBoxTracker] = []
        self._frame_count = 0
        KalmanBoxTracker._count = 0  # Reinicia IDs

    def reset(self):
        """Reinicia o tracker (novo lote, nova camara, etc.)."""
        self._tracks = []
        self._frame_count = 0
        KalmanBoxTracker._count = 0
        logger.info("[Tracker] Reiniciado.")

    def update(self, detections: List[Dict]) -> List[Dict]:
        """
        Atualiza o tracker com as deteccoes do frame atual.

        Args:
            detections: lista de dicts com:
                bbox       : [x1, y1, x2, y2]
                confidence : float
                class_id   : int
                mask_area_px: float (opcional, para segmentacao)

        Retorna:
            lista de dicts com os tracks ativos:
                track_id  : int (persistente entre frames)
                bbox      : [x1, y1, x2, y2] (posicao atualizada)
                centroid  : (cx, cy)
                confidence: float
                class_id  : int
                state     : "TENTATIVE" | "CONFIRMED"
                age       : int (frames de vida)
                mask_area_px: float
        """
        self._frame_count += 1

        # ── Passo 1: Predicao de todos os tracks ──────────────────────────────
        for trk in self._tracks:
            trk.predict()

        # ── Passo 2: Separar deteccoes por nivel de confianca ─────────────────
        high_dets = [d for d in detections if d.get("confidence", 0) >= TRACK_HIGH_THRESH]
        low_dets = [
            d for d in detections if TRACK_LOW_THRESH <= d.get("confidence", 0) < TRACK_HIGH_THRESH
        ]

        active_tracks = [t for t in self._tracks if t.time_since_update <= 1]
        lost_tracks = [t for t in self._tracks if t.time_since_update > 1]

        # ── Passo 3a: Associacao de ALTA confianca com tracks ativos ──────────
        trk_bboxes = [t.get_predicted_bbox() for t in active_tracks]
        det_bboxes = [d["bbox"] for d in high_dets]
        iou_mat = _iou_matrix(det_bboxes, trk_bboxes)
        matches_h, unmatched_det_h, unmatched_trk_h = _greedy_match(iou_mat, 1.0 - MATCH_THRESH)

        for det_idx, trk_idx in matches_h:
            d = high_dets[det_idx]
            active_tracks[trk_idx].update(d["bbox"], d.get("confidence", 1.0), d.get("class_id", 0))

        # ── Passo 3b: Associacao de BAIXA confianca com tracks perdidos ───────
        remaining_lost = lost_tracks + [active_tracks[i] for i in unmatched_trk_h]
        low_det_bboxes = [d["bbox"] for d in low_dets]
        lost_bboxes = [t.get_predicted_bbox() for t in remaining_lost]
        iou_mat_low = _iou_matrix(low_det_bboxes, lost_bboxes)
        matches_l, unmatched_det_l, _ = _greedy_match(iou_mat_low, 1.0 - MATCH_THRESH)

        for det_idx, trk_idx in matches_l:
            d = low_dets[det_idx]
            remaining_lost[trk_idx].update(
                d["bbox"], d.get("confidence", 1.0), d.get("class_id", 0)
            )

        # ── Passo 4: Criar novas tracks para deteccoes nao associadas ─────────
        for det_idx in unmatched_det_h:
            d = high_dets[det_idx]
            if d.get("confidence", 0) >= NEW_TRACK_THRESH:
                trk = KalmanBoxTracker(d["bbox"])
                trk.confidence = d.get("confidence", 1.0)
                trk.class_id = d.get("class_id", 0)
                self._tracks.append(trk)

        # ── Passo 5: Marcar tracks como LOST ou remover definitivamente ────────
        to_remove = []
        for trk in self._tracks:
            if trk.time_since_update > TRACK_BUFFER:
                trk.state = "LOST"
            if trk.time_since_update > MAX_TIME_LOST:
                to_remove.append(trk)

        for trk in to_remove:
            self._tracks.remove(trk)

        # ── Passo 6: Retornar apenas tracks confirmadas e tentativas recentes ──
        output = []
        for trk in self._tracks:
            if trk.state in ("CONFIRMED", "TENTATIVE") and trk.time_since_update <= TRACK_BUFFER:
                bbox = trk.get_predicted_bbox()
                output.append(
                    {
                        "track_id": trk.track_id,
                        "bbox": bbox,
                        "centroid": trk.get_centroid(),
                        "confidence": trk.confidence,
                        "class_id": trk.class_id,
                        "state": trk.state,
                        "age": trk.age,
                        "hit_streak": trk.hit_streak,
                        "mask_area_px": 0.0,
                    }
                )

        return output

    @property
    def track_count(self) -> int:
        return sum(1 for t in self._tracks if t.state == "CONFIRMED")

    @property
    def all_track_ids(self) -> List[int]:
        return [t.track_id for t in self._tracks]
