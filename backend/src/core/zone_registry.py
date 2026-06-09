"""
ChikGuard -- ZoneRegistry v1 (Anti-Duplicata por Zona/Linha)
=============================================================
Garante que cada pintinho (track_id) so seja "registrado" (salvo no banco)
UMA UNICA VEZ, independente de quantos frames ele apareca.

Duas estrategias geometricas:
  A) Linha Virtual de Contagem (Line Crossing):
     - Uma linha virtual divide o frame
     - Quando o centroide de um track cruza a linha (troca de lado), ele e registrado
     - Implementado via produto vetorial do vetor de direcao
     - Ideal para cameras com angulo lateral (pintinhos passam pela linha)

  B) Zona de Registro (Registration Zone):
     - Um poligono convexo define a "zona de registro"
     - Quando o centroide entra na zona pela primeira vez, o track e registrado
     - Ideal para cameras zenitais (visao de cima) ou pontos de entrada/saida

Matematica:
  Line Crossing: sign(cross(P1P2, P1C)) muda de iteracao para iteracao
  Point in Polygon: ray-casting algorithm O(N) para poligono convexo

Integracao no camera_loop:
    registry = ZoneRegistry(strategy="zone", zone_polygon=[(100,200), (500,200), (500,400), (100,400)])
    for track in tracked_objects:
        event = registry.process(track["track_id"], track["centroid"])
        if event:
            # event.track_id e novo -- salvar no banco
            await uploader.enqueue(frame, track, mask)
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger("chikguard.zone_registry")

# ── Configuracao via ENV ──────────────────────────────────────────────────────
# Estrategia: "line" | "zone"
REGISTRY_STRATEGY = os.getenv("REGISTRY_STRATEGY", "zone").strip().lower()

# Linha virtual (coordenadas normalizadas 0.0-1.0, para ser independente de resolucao)
# Format: "x1_norm,y1_norm,x2_norm,y2_norm"
# Exemplo: "0.0,0.5,1.0,0.5" = linha horizontal no meio do frame
LINE_P1_NORM = tuple(float(v) for v in os.getenv("REGISTRY_LINE_P1", "0.0,0.5").split(","))
LINE_P2_NORM = tuple(float(v) for v in os.getenv("REGISTRY_LINE_P2", "1.0,0.5").split(","))

# Zona de registro (porcentagem do frame) em formato "x1,y1,x2,y2" (top-left, bottom-right)
ZONE_RECT = tuple(float(v) for v in os.getenv("REGISTRY_ZONE_RECT", "0.1,0.1,0.9,0.9").split(","))


@dataclass
class RegistrationEvent:
    """Emitido quando um track_id cruza a linha ou entra na zona pela primeira vez."""

    track_id: int
    centroid: Tuple[float, float]
    timestamp: float = field(default_factory=time.time)
    strategy: str = "zone"
    frame_index: int = 0


# =============================================================================
# Geometria 2D
# =============================================================================


def _cross_2d(ax: float, ay: float, bx: float, by: float) -> float:
    """Produto vetorial 2D: ax*by - ay*bx."""
    return ax * by - ay * bx


def _side_of_line(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    point: Tuple[float, float],
) -> float:
    """
    Retorna o sinal do produto vetorial (p2-p1) x (point-p1).
    > 0: ponto esta a esquerda da linha p1->p2
    < 0: ponto esta a direita da linha p1->p2
    = 0: ponto sobre a linha
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    px = point[0] - p1[0]
    py = point[1] - p1[1]
    return _cross_2d(dx, dy, px, py)


def _point_in_polygon(
    point: Tuple[float, float],
    polygon: List[Tuple[float, float]],
) -> bool:
    """
    Ray-casting algorithm: ponto dentro de poligono arbitrario.
    O(N) onde N = numero de vertices.
    Funciona para poligonos convexos e concavos.
    """
    px, py = point
    n = len(polygon)
    inside = False

    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi):
            inside = not inside
        j = i

    return inside


def _scale_point(
    point: Tuple[float, float],
    frame_w: int,
    frame_h: int,
) -> Tuple[float, float]:
    """Converte coordenadas normalizadas [0,1] para pixels."""
    return point[0] * frame_w, point[1] * frame_h


# =============================================================================
# ZoneRegistry — Nucleo de anti-duplicata
# =============================================================================


class ZoneRegistry:
    """
    Registro de pintinhos sem duplicata via geometria de zona ou linha.

    Garante que cada track_id seja processado/salvo UMA UNICA VEZ,
    independentemente de quantos frames ou quanto tempo ele apareca.

    Uso com Zona:
        registry = ZoneRegistry(
            strategy="zone",
            zone_polygon=[(100,100), (600,100), (600,400), (100,400)],
        )

    Uso com Linha:
        registry = ZoneRegistry(
            strategy="line",
            line_p1=(0, 360),       # coordenadas em pixels
            line_p2=(1280, 360),
        )

    No loop:
        event = registry.process(track_id, centroid, frame_w=1280, frame_h=720)
        if event:
            # Novo pintinho validado! Disparar salvamento assincrono.
            await uploader.enqueue(...)
    """

    def __init__(
        self,
        strategy: str = REGISTRY_STRATEGY,
        # Zona
        zone_polygon: Optional[List[Tuple[float, float]]] = None,
        zone_rect_norm: Optional[Tuple[float, float, float, float]] = None,
        # Linha
        line_p1: Optional[Tuple[float, float]] = None,
        line_p2: Optional[Tuple[float, float]] = None,
    ):
        self.strategy = strategy.lower()

        # ── Zona de registro ────────────────────────────────────────────────
        if zone_polygon:
            self._zone: List[Tuple[float, float]] = zone_polygon
        else:
            # Cria poligono retangular a partir de zona normalizada ou ENV
            rect = zone_rect_norm or ZONE_RECT
            x1n, y1n, x2n, y2n = rect
            # Sera escalonado no momento do processo (multiplos frames podem ter res. diferente)
            self._zone_norm: Tuple[float, float, float, float] = (x1n, y1n, x2n, y2n)
            self._zone = []  # calculado dinamicamente

        # ── Linha virtual ───────────────────────────────────────────────────
        self._line_p1_norm = line_p1 or tuple(
            float(v) for v in os.getenv("REGISTRY_LINE_P1", "0.0,0.5").split(",")
        )
        self._line_p2_norm = line_p2 or tuple(
            float(v) for v in os.getenv("REGISTRY_LINE_P2", "1.0,0.5").split(",")
        )

        # ── Estado interno ──────────────────────────────────────────────────
        self._registered: Set[int] = set()  # track_ids ja registrados
        self._last_side: Dict[int, float] = {}  # lado anterior (line strategy)
        self._frame_index: int = 0

        logger.info("[ZoneRegistry] Estrategia: %s", self.strategy)

    # ── API principal ─────────────────────────────────────────────────────────

    def process(
        self,
        track_id: int,
        centroid: Tuple[float, float],
        frame_w: int = 1280,
        frame_h: int = 720,
    ) -> Optional[RegistrationEvent]:
        """
        Processa um track e retorna um RegistrationEvent se for o PRIMEIRO
        registro deste track_id.

        Retorna None se:
          - track_id ja foi registrado anteriormente (anti-duplicata)
          - centroide ainda nao cruzou a linha / entrou na zona
        """
        self._frame_index += 1

        # Anti-duplicata: track ja foi registrado?
        if track_id in self._registered:
            return None

        triggered = False

        if self.strategy == "line":
            triggered = self._check_line(track_id, centroid, frame_w, frame_h)
        else:
            triggered = self._check_zone(centroid, frame_w, frame_h)

        if triggered:
            self._registered.add(track_id)
            logger.info(
                "[ZoneRegistry] NOVO registro: track_id=%d centroid=(%.0f, %.0f)",
                track_id,
                centroid[0],
                centroid[1],
            )
            return RegistrationEvent(
                track_id=track_id,
                centroid=centroid,
                strategy=self.strategy,
                frame_index=self._frame_index,
            )

        return None

    def is_registered(self, track_id: int) -> bool:
        """Verifica se um track_id ja foi registrado."""
        return track_id in self._registered

    def force_register(self, track_id: int):
        """Registra manualmente um track_id (para testes ou override)."""
        self._registered.add(track_id)

    def total_registered(self) -> int:
        return len(self._registered)

    def reset(self):
        """Limpa todos os registros (novo turno de monitoramento)."""
        self._registered.clear()
        self._last_side.clear()
        self._frame_index = 0
        logger.info("[ZoneRegistry] Registros limpos.")

    # ── Estrategias internas ──────────────────────────────────────────────────

    def _check_line(
        self,
        track_id: int,
        centroid: Tuple[float, float],
        frame_w: int,
        frame_h: int,
    ) -> bool:
        """
        Detecta cruzamento de linha virtual.

        Matematica:
          - Calcula o sinal do produto vetorial entre o vetor da linha e o vetor
            do ponto inicial da linha ao centroide.
          - Se o sinal muda de um frame para o outro, o ponto cruzou a linha.
        """
        p1 = (self._line_p1_norm[0] * frame_w, self._line_p1_norm[1] * frame_h)
        p2 = (self._line_p2_norm[0] * frame_w, self._line_p2_norm[1] * frame_h)

        current_side = _side_of_line(p1, p2, centroid)

        # Primeiro frame deste track: registra apenas o lado sem disparar
        if track_id not in self._last_side:
            self._last_side[track_id] = current_side
            return False

        prev_side = self._last_side[track_id]
        self._last_side[track_id] = current_side

        # Cruzamento detectado quando o sinal muda (de + para - ou vice-versa)
        # Ignoramos o caso em que ambos sao zero (centroide SOBRE a linha)
        if prev_side != 0 and current_side != 0:
            if (prev_side > 0) != (current_side > 0):
                return True

        return False

    def _check_zone(
        self,
        centroid: Tuple[float, float],
        frame_w: int,
        frame_h: int,
    ) -> bool:
        """
        Detecta entrada do centroide na zona de registro.
        Suporta poligono arbitrario ou retangulo normalizado.
        """
        # Constroi poligono em pixels se usando zona normalizada
        if not self._zone and hasattr(self, "_zone_norm"):
            x1n, y1n, x2n, y2n = self._zone_norm
            self._zone = [
                (x1n * frame_w, y1n * frame_h),
                (x2n * frame_w, y1n * frame_h),
                (x2n * frame_w, y2n * frame_h),
                (x1n * frame_w, y2n * frame_h),
            ]

        return _point_in_polygon(centroid, self._zone)

    # ── Visualizacao ──────────────────────────────────────────────────────────

    def draw_overlay(self, frame, frame_w: int = 1280, frame_h: int = 720):
        """
        Desenha a zona/linha de registro no frame para visualizacao.
        Retorna o frame com o overlay.
        """
        import cv2

        draw = frame.copy()
        color_active = (0, 255, 255)  # ciano
        color_text = (255, 255, 255)  # branco

        if self.strategy == "line":
            p1 = (int(self._line_p1_norm[0] * frame_w), int(self._line_p1_norm[1] * frame_h))
            p2 = (int(self._line_p2_norm[0] * frame_w), int(self._line_p2_norm[1] * frame_h))
            cv2.line(draw, p1, p2, color_active, 2, cv2.LINE_AA)
            cv2.putText(
                draw,
                f"LINHA CONTAGEM | REG: {self.total_registered()}",
                (p1[0] + 5, p1[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color_text,
                1,
                cv2.LINE_AA,
            )
        else:
            if self._zone:
                pts = np.array([(int(x), int(y)) for x, y in self._zone], dtype=np.int32)
                overlay = draw.copy()
                cv2.fillPoly(overlay, [pts], (0, 200, 200))
                cv2.addWeighted(overlay, 0.12, draw, 0.88, 0, draw)
                cv2.polylines(
                    draw,
                    [pts],
                    isClosed=True,
                    color=color_active,
                    thickness=2,
                    lineType=cv2.LINE_AA,
                )
                cx = int(np.mean(pts[:, 0]))
                cy = int(np.mean(pts[:, 1]))
                cv2.putText(
                    draw,
                    f"ZONA REG | {self.total_registered()} salvos",
                    (cx - 70, cy),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.50,
                    color_text,
                    1,
                    cv2.LINE_AA,
                )

        return draw
