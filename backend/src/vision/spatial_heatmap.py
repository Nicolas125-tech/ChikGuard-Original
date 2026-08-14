import time
import math
import threading
import numpy as np
from typing import List, Tuple, Dict, Any


class SpatialHeatmapAccumulator:
    """
    Acumulador de Densidade Espacial 2D/3D baseado em Visão Computacional.
    
    Coleta centroides `(cx, cy)` de aves detectadas pela câmera e acumula
    frequências de permanência numa grade regular `(grid_size x grid_size)`.
    """

    def __init__(self, default_grid_size: int = 40, history_decay_sec: float = 3600.0):
        self.default_grid_size = default_grid_size
        self.history_decay_sec = history_decay_sec
        self._lock = threading.Lock()
        
        # Histórico de pontos: list of (x_norm, y_norm, timestamp)
        self._points: List[Tuple[float, float, float]] = []

    def add_detections(self, centers: List[Tuple[float, float]], frame_width: int, frame_height: int, timestamp: float = None):
        """
        Adiciona posições de centroides de aves normalizadas (0.0 a 1.0) para acumulação.
        """
        if not centers or frame_width <= 0 or frame_height <= 0:
            return

        ts = timestamp if timestamp is not None else time.time()
        
        new_pts = []
        for cx, cy in centers:
            x_norm = max(0.0, min(1.0, cx / float(frame_width)))
            y_norm = max(0.0, min(1.0, cy / float(frame_height)))
            new_pts.append((x_norm, y_norm, ts))

        with self._lock:
            self._points.extend(new_pts)
            # Limpeza de pontos mais antigos que history_decay_sec
            cutoff = ts - self.history_decay_sec
            self._points = [pt for pt in self._points if pt[2] >= cutoff]

    def get_grid_matrix(self, grid_size: int = None, hours: float = 24.0) -> np.ndarray:
        """
        Gera a matriz de densidade espacial `(grid_size x grid_size)` normalizada entre 0.0 e 1.0.
        """
        g_size = grid_size if grid_size is not None else self.default_grid_size
        g_size = max(8, min(g_size, 128))
        
        matrix = np.zeros((g_size, g_size), dtype=np.float32)
        
        now = time.time()
        cutoff = now - (hours * 3600.0)

        with self._lock:
            valid_pts = [pt for pt in self._points if pt[2] >= cutoff]

        if not valid_pts:
            return matrix

        for x_norm, y_norm, _ in valid_pts:
            col = int(x_norm * (g_size - 1))
            row = int(y_norm * (g_size - 1))
            matrix[row, col] += 1.0

        max_val = np.max(matrix)
        if max_val > 0:
            matrix = matrix / max_val

        return matrix

    def get_3d_points(self, grid_size: int = 24, hours: float = 24.0) -> List[Dict[str, Any]]:
        """
        Retorna pontos formatados em estrutura voxel 3D (X, Y, Z_densidade) para o Gêmeo Digital.
        """
        matrix = self.get_grid_matrix(grid_size=grid_size, hours=hours)
        points_3d = []
        rows, cols = matrix.shape

        for r in range(rows):
            for c in range(cols):
                val = float(matrix[r, c])
                if val > 0.01:
                    points_3d.append({
                        "x": c,
                        "y": r,
                        "z": round(val, 3),
                        "density": round(val, 3)
                    })

        return points_3d
