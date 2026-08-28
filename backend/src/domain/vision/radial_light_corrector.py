import math
import numpy as np
import cv2
from typing import Tuple


class RadialBrooderLightCorrector:
    """
    Corretor Radial de Iluminação Central de Aquecimento (Campânula).
    Baseado nas Equações (1) a (4) e Seção 3.1 do artigo científico (Saltoratto et al., 2013).
    
    Técnica:
      1. Conversão do espaço RGB/BGR para HSI (Matiz H, Saturação S, Intensidade I).
      2. Aplicação da Equação da Circunferência x^2 + y^2 = R^2 a partir do centro do ponto de luz.
      3. Redução gradual de até 40% da intensidade I no centro, atenuando linearmente (fator 0.4 / (r_max - r_min))
         à medida que o raio aumenta de r_min a r_max.
      4. Re-conversão para HSI/BGR.
    """

    def __init__(
        self,
        center_xy: Tuple[int, int] = None,
        r_min: float = 70.0,
        r_max: float = 275.0,
        max_attenuation: float = 0.40,
    ):
        self.center_xy = center_xy
        self.r_min = r_min
        self.r_max = r_max
        self.max_attenuation = max_attenuation

    def bgr_to_hsi(self, bgr_img: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Converte imagem BGR para os canais H (Matiz), S (Saturação) e I (Intensidade)
        conforme as Equações (1), (2) e (3) do artigo.
        """
        img = bgr_img.astype(np.float32) / 255.0
        b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]

        # Canal I (Intensidade/Brilho) - Equação (3): I = 1/3 * (R + G + B)
        intensity = (r + g + b) / 3.0

        # Canal S (Saturação) - Equação (2): S = 1 - (3 / (R+G+B)) * min(R,G,B)
        min_rgb = np.minimum(np.minimum(r, g), b)
        sum_rgb = r + g + b
        saturation = np.zeros_like(intensity)
        mask_sum = sum_rgb > 1e-6
        saturation[mask_sum] = 1.0 - (3.0 / sum_rgb[mask_sum]) * min_rgb[mask_sum]

        # Canal H (Matiz) - Equação (1)
        num = 0.5 * ((r - g) + (r - b))
        den = np.sqrt((r - g) ** 2 + (r - b) * (g - b)) + 1e-6
        theta = np.arccos(np.clip(num / den, -1.0, 1.0))

        hue = np.zeros_like(intensity)
        mask_b = b > g
        hue[mask_b] = 2.0 * np.pi - theta[mask_b]
        hue[~mask_b] = theta[~mask_b]

        return hue, saturation, intensity

    def correct_intensity(self, frame: np.ndarray) -> np.ndarray:
        """
        Aplica a redução de brilho radial circular na região central da iluminação da baia.
        """
        if frame is None or frame.size == 0:
            return frame

        h, w = frame.shape[:2]
        cx, cy = self.center_xy if self.center_xy is not None else (int(w / 2), int(h / 2))

        # Converte para HSI
        hue, sat, intensity = self.bgr_to_hsi(frame)

        # Gera grade de coordenadas cartesianas relativas à origem (cx, cy) - Equação (4)
        y_indices, x_indices = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x_indices - cx) ** 2 + (y_indices - cy) ** 2)

        # Calcula o fator de atenuação gradual circular (40% no centro caindo a 0% no raio r_max)
        attenuation_mask = np.zeros_like(intensity)
        
        # Região r < r_min: atenuação máxima de 40%
        mask_inner = dist_from_center <= self.r_min
        attenuation_mask[mask_inner] = self.max_attenuation

        # Região r_min < r <= r_max: atenuação decrescente linear
        mask_ring = (dist_from_center > self.r_min) & (dist_from_center <= self.r_max)
        ring_dists = dist_from_center[mask_ring]
        decay_factor = (self.r_max - ring_dists) / (self.r_max - self.r_min)
        attenuation_mask[mask_ring] = self.max_attenuation * decay_factor

        # Aplica a redução da intensidade I
        corrected_intensity = np.clip(intensity * (1.0 - attenuation_mask), 0.0, 1.0)

        # Converte HSI de volta para BGR (versão vetorizada simplificada)
        # Para performance de tempo real no loop de vídeo, aplica a atenuação nos canais BGR diretamente
        # preservando a matriz de cor original
        attenuation_3ch = np.dstack([attenuation_mask] * 3)
        corrected_bgr = np.clip(frame.astype(np.float32) * (1.0 - attenuation_3ch), 0.0, 255.0).astype(np.uint8)

        return corrected_bgr
