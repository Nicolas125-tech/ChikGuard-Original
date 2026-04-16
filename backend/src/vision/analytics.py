import cv2
import numpy as np
import time
# from backend.database import db # Assuming a generic db setup, might need adjustment based on actual models
# Note: In a real implementation, you would import the specific SQLAlchemy
# model


class AnalyticsEngine:
    """
    Exporta métricas de densidade e atividade para a base de dados
    """

    def __init__(self, export_interval_seconds=60):
        self.export_interval = export_interval_seconds
        self.last_export_time = time.time()
        self._activity_buffer = []
        self._density_buffer = []

    def log_metrics(self, density, activity_pixels_per_sec):
        """Acumula métricas no buffer"""
        self._density_buffer.append(density)
        self._activity_buffer.append(activity_pixels_per_sec)

        current_time = time.time()
        if current_time - self.last_export_time >= self.export_interval:
            self.export_to_database()
            self.last_export_time = current_time

    def export_to_database(self):
        """Calcula médias e salva no DB (mock for now, replace with actual DB call)"""
        if not self._density_buffer or not self._activity_buffer:
            return

        avg_density = sum(self._density_buffer) / len(self._density_buffer)
        avg_activity = sum(self._activity_buffer) / len(self._activity_buffer)

        print(
            f"[Analytics] Exportando: Densidade Media={
                avg_density:.2f}, Atividade Media={
                avg_activity:.2f} px/s")

        # Here you would typically do:
        # new_metric = MetricModel(density=avg_density, activity=avg_activity)
        # db.session.add(new_metric)
        # db.session.commit()

        # Limpar buffers após exportar
        self._density_buffer = []
        self._activity_buffer = []


class HeatmapGenerator:
    """
    Gera mapas de ocupação (heatmaps) acumulando posições das aves.
    Útil para identificar áreas mais frequentadas e problemas de distribuição (ex: água/ração).
    """

    def __init__(
            self,
            frame_size=(
                480,
                640),
            decay_rate=0.05,
            max_intensity=255):
        self.frame_height, self.frame_width = frame_size[:2]
        self.heatmap = np.zeros(
            (self.frame_height, self.frame_width), dtype=np.float32)
        self.decay_rate = decay_rate
        self.max_intensity = max_intensity

    def update(self, detections):
        """
        Atualiza o heatmap com as novas detecções.
        detections: list of dicts with 'box' [x1, y1, x2, y2]
        """
        # Decaimento temporal para destacar áreas atuais (opcional, pode ser
        # ajustado)
        self.heatmap -= self.decay_rate
        self.heatmap = np.maximum(self.heatmap, 0)

        for det in detections:
            box = det.get("box", [0, 0, 1, 1])
            x1, y1, x2, y2 = [int(v) for v in box]

            # Centroide da base da ave (onde ela pisa) é mais representativo
            cx = int((x1 + x2) / 2)
            cy = y2

            # Raio de influência da presença
            radius = int((x2 - x1) / 2)

            # Adiciona intensidade na posição (usando um circulo ou gaussian)
            # Para performance, um circulo simples preenchido
            if 0 <= cx < self.frame_width and 0 <= cy < self.frame_height:
                # Criar uma máscara temporária para adicionar intensidade
                # suavemente
                temp_mask = np.zeros_like(self.heatmap)
                cv2.circle(temp_mask, (cx, cy), radius, 5.0, -1)
                self.heatmap += temp_mask

        self.heatmap = np.minimum(self.heatmap, self.max_intensity)

    def get_heatmap_image(self, colormap=cv2.COLORMAP_JET):
        """
        Retorna a imagem do heatmap com o colormap aplicado.
        """
        normalized = cv2.normalize(
            self.heatmap,
            None,
            0,
            255,
            cv2.NORM_MINMAX,
            dtype=cv2.CV_8U)
        colored_heatmap = cv2.applyColorMap(normalized, colormap)
        return colored_heatmap

    def overlay_on_frame(self, frame, alpha=0.5):
        """
        Sobrepõe o heatmap no frame original.
        """
        colored_heatmap = self.get_heatmap_image()
        # Ensure sizes match
        if frame.shape[:2] != colored_heatmap.shape[:2]:
            colored_heatmap = cv2.resize(
                colored_heatmap, (frame.shape[1], frame.shape[0]))
        return cv2.addWeighted(colored_heatmap, alpha, frame, 1 - alpha, 0)


class BehaviorAnalyzer:
    """
    Analisa comportamentos avançados como agrupamentos anômalos (Crowding)
    """

    def __init__(self, crowding_threshold=0.85):
        # Ex: 85% concentrados em pequena área
        self.crowding_threshold = crowding_threshold

    def analyze_crowding(self, detections, frame_size=(480, 640)):
        """
        Retorna True se houver indicativo de crowding (muitas aves agrupadas).
        """
        if len(detections) < 5:
            return False, 0.0

        h, w = frame_size[:2]
        # total_area = h * w

        # Simple heuristic: calculate bounding box of all detections
        min_x, min_y = w, h
        max_x, max_y = 0, 0

        for det in detections:
            box = det.get("box", [0, 0, 1, 1])
            x1, y1, x2, y2 = [int(v) for v in box]
            min_x, min_y = min(min_x, x1), min(min_y, y1)
            max_x, max_y = max(max_x, x2), max(max_y, y2)

        group_area = max(1, (max_x - min_x) * (max_y - min_y))

        # Average area per bird
        bird_areas = []
        for det in detections:
            box = det.get("box", [0, 0, 1, 1])
            x1, y1, x2, y2 = [int(v) for v in box]
            bird_areas.append((x2 - x1) * (y2 - y1))

        avg_bird_area = sum(bird_areas) / len(bird_areas)
        expected_group_area = avg_bird_area * \
            len(detections) * 1.5  # 1.5 is a spacing factor

        # If the actual group area is significantly smaller than expected, it
        # means they are packed tightly
        dispersion_ratio = group_area / expected_group_area

        # If dispersion ratio is low, crowding is happening
        is_crowding = dispersion_ratio < self.crowding_threshold

        return is_crowding, dispersion_ratio


class ROIConfig:
    """
    Gerenciador de Region of Interest (Zonas de Exclusão)
    """

    def __init__(self):
        self.rois = []  # List of polygons/rects

    def add_rect_roi(self, x1, y1, x2, y2):
        self.rois.append({'type': 'rect', 'coords': (x1, y1, x2, y2)})

    def clear(self):
        self.rois = []

    def is_inside_roi(self, x, y):
        if not self.rois:
            return True  # If no ROIs, everything is monitored

        for roi in self.rois:
            if roi['type'] == 'rect':
                x1, y1, x2, y2 = roi['coords']
                if x1 <= x <= x2 and y1 <= y <= y2:
                    return True
        return False

    def filter_detections(self, detections):
        """
        Remove detecções fora da zona de interesse.
        """
        if not self.rois:
            return detections

        filtered = []
        for det in detections:
            box = det.get("box", [0, 0, 1, 1])
            x1, y1, x2, y2 = [int(v) for v in box]
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            if self.is_inside_roi(cx, cy):
                filtered.append(det)

        return filtered
