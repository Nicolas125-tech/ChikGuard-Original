import cv2
import numpy as np
from typing import Tuple, Dict, Any


class PaperBackgroundSubtractor:
    """
    Subtrator de Fundo e Segmentação por Inundação (Flood Fill) & Operação Morfológica de Fecho.
    Baseado em Saltoratto et al. (2013), Seção 3.1 & Equações (5) a (9).
    
    Etapas:
      1. Armazena imagem de fundo estática da baia sem aves (h(x,y)).
      2. Aplica imagem negativa g(x,y) = W - f(x,y) (Equação 5).
      3. Executa a subtração de fundo f(x,y) = g(x,y) - h(x,y) (Equação 6).
      4. Aplica a operação morfológica de Fecho A • B = (A ⊕ B) ⊖ B (Dilatação + Erosão) (Equações 7-9).
      5. Aplica limiarização com limiar empiricamente definido em 150.
      6. Aplica algoritmo de Inundação (Flood Fill) para contagem de blobs de aves e massa de pixels.
    """

    def __init__(self, threshold_val: int = 150, morph_kernel_size: int = 5):
        self.threshold_val = threshold_val
        self.kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (morph_kernel_size, morph_kernel_size))
        self.background_frame: np.ndarray = None

    def set_background(self, bg_frame: np.ndarray):
        """
        Define a imagem de fundo estática da baia sem a presença de aves (h(x,y)).
        """
        if bg_frame is not None and bg_frame.size > 0:
            if bg_frame.ndim == 3:
                gray = cv2.cvtColor(bg_frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = bg_frame
            # Negative of background
            self.background_frame = 255 - gray

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Subtrai o fundo, aplica Fecho morfológico e Flood Fill.
        """
        if frame is None or frame.size == 0:
            return {
                "blobs_count": 0,
                "total_mask_area": 0,
                "mask": None,
                "blobs_centers": [],
            }

        if frame.ndim == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # Equação (5): Imagem em Negativo g(x,y) = 255 - f(x,y)
        neg_frame = 255 - gray

        # Equação (6): Subtração com a imagem de fundo em negativo
        if self.background_frame is not None and self.background_frame.shape == neg_frame.shape:
            subtracted = cv2.absdiff(neg_frame, self.background_frame)
        else:
            subtracted = neg_frame

        # Limiarização com valor empiricamente definido = 150
        ret, thresh = cv2.threshold(subtracted, self.threshold_val, 255, cv2.THRESH_BINARY)

        # Equações (7-9): Operação Morfológica de FECHO: Dilatação seguida de Erosão (A • B)
        closing = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, self.kernel)

        # Algoritmo de Inundação (Flood Fill) / Componentes Conectados para encontrar centroides e área de massa
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(closing, connectivity=8)

        blobs_centers = []
        total_area = 0

        # Filtra componente de fundo (label 0)
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= 25:  # Filtra ruídos mínimos
                total_area += area
                cx, cy = centroids[i]
                blobs_centers.append((float(cx), float(cy)))

        return {
            "blobs_count": len(blobs_centers),
            "total_mask_area": int(total_area),
            "mask": closing,
            "blobs_centers": blobs_centers,
        }
