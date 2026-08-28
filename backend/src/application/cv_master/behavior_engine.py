import logging
import math
import time
from typing import Dict, List, Set, Tuple

try:
    import supervision as sv
except ImportError:
    pass


class BehaviorEngine:
    def __init__(self, heatmap_opacity=0.5, immobility_threshold=10.0, immobility_time_sec=120):
        """
        Módulo de Comportamento Avançado.
        Gera Heatmaps (Zonas Quentes).
        Gera Alarmes de Imobilidade se um alvo mover < threshold (pixels) por tempo prolongado.
        Calcula o Índice de Agrupamento (Huddling) para inferir conforto térmico das aves.
        """
        self.logger = logging.getLogger("cv_master.BehaviorEngine")

        # Heatmap (requer biblioteca supervision)
        if "sv" in globals() and sv is not None:
            try:
                self.heatmap_annotator = sv.HeatMapAnnotator(
                    position=sv.Position.CENTER,
                    opacity=heatmap_opacity,
                    radius=20,
                    kernel_size=25,
                    cell_size=10,
                )
            except Exception:
                self.heatmap_annotator = None
        else:
            self.heatmap_annotator = None

        # Imobilidade (X, Y, Timestamp)
        self.track_history = {}  # ID: { x, y, ts, last_seen }
        self.immobility_threshold = immobility_threshold
        self.immobility_time_sec = immobility_time_sec
        self.dead_or_sick_ids = set()

        self.logger.info("Engrenagem de Comportamento e Heatmap Inicializada.")

    def update_immobility_and_get_alerts(self, detections) -> List[Dict]:
        """
        Analisa as detecções, calcula a distância de imobilidade e retorna dicionários de alertas.
        Retorna: [{"track_id": int, "box": list, "seconds_still": float, "message": str}]
        """
        alerts = []
        current_time = time.time()

        if detections is None or len(detections) == 0 or detections.tracker_id is None:
            return alerts

        for i in range(len(detections)):
            if detections.tracker_id[i] is None:
                continue

            track_id = int(detections.tracker_id[i])
            box = detections.xyxy[i].tolist()

            # Centroide
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0

            if track_id not in self.track_history:
                self.track_history[track_id] = {
                    "x": cx,
                    "y": cy,
                    "ts": current_time,
                    "last_seen": current_time,
                }
            else:
                hist = self.track_history[track_id]
                dist = math.hypot(cx - hist["x"], cy - hist["y"])

                # Se moveu mais que o threshold, reseta o tempo e a âncora
                if dist > self.immobility_threshold:
                    hist["x"] = cx
                    hist["y"] = cy
                    hist["ts"] = current_time
                    if track_id in self.dead_or_sick_ids:
                        self.dead_or_sick_ids.remove(track_id)
                else:
                    # Imóvel. Há quanto tempo?
                    time_inactive = current_time - hist["ts"]
                    if time_inactive > self.immobility_time_sec:
                        self.dead_or_sick_ids.add(track_id)
                        alerts.append({
                            "track_id": track_id,
                            "box": box,
                            "seconds_still": time_inactive,
                            "message": f"ALERTA: Ave #{track_id} imóvel há {int(time_inactive)}s."
                        })

                hist["last_seen"] = current_time

        # Cleanup: remover IDs que não são vistos há mais de 30 segundos
        ids_to_del = [
            tid
            for tid, data in self.track_history.items()
            if (current_time - data["last_seen"]) > 30.0
        ]
        for tid in ids_to_del:
            del self.track_history[tid]
            if tid in self.dead_or_sick_ids:
                self.dead_or_sick_ids.remove(tid)

        return alerts

    def calculate_clustering_index(self, detections) -> Tuple[float, str]:
        """
        Calcula o índice de agrupamento (Huddling Index) das aves detectadas.
        Regra de Negócio Zootécnica: 
          - Baixa distância média entre indivíduos indica frio (aves se amontoam / huddling).
          - Distância normal indica conforto térmico.
          - Alta dispersão indica calor excessivo.
        Retorna (avg_distance, status_label)
        """
        if detections is None or len(detections) < 2:
            return 0.0, "NORMAL"

        centroids = []
        for box in detections.xyxy:
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0
            centroids.append((cx, cy))

        total_dist = 0.0
        pairs = 0
        for i in range(len(centroids)):
            for j in range(i + 1, len(centroids)):
                total_dist += math.hypot(centroids[i][0] - centroids[j][0], centroids[i][1] - centroids[j][1])
                pairs += 1

        avg_dist = total_dist / pairs if pairs > 0 else 0.0

        # Limites zootécnicos baseados em frame padrão de 640x480 / 1280x720
        if avg_dist < 120.0:
            return avg_dist, "AGRUPADA (FRIO)"
        elif avg_dist > 320.0:
            return avg_dist, "DISPERSA (CALOR)"
        else:
            return avg_dist, "CONFORTO TÉRMICO"

    def annotate_heatmap(self, frame, detections):
        """
        Aplica o mapa de calor no frame
        """
        if self.heatmap_annotator is None or detections is None or len(detections) == 0:
            return frame
