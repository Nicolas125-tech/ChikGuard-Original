import logging
import time
import math
import cv2

try:
    import supervision as sv
except ImportError:
    pass

class BehaviorEngine:
    def __init__(self, heatmap_opacity=0.5, immobility_threshold=5.0, immobility_time_sec=300):
        """
        Módulo de Comportamento.
        Gera Heatmaps (Zonas Quentes).
        Gera Alarmes de Imobilidade se um alvo mover < threshold (pixels) por tempo prolongado.
        """
        self.logger = logging.getLogger("cv_master.BehaviorEngine")
        
        # Heatmap
        self.heatmap_annotator = sv.HeatMapAnnotator(
            position=sv.Position.CENTER,
            opacity=heatmap_opacity,
            radius=20,
            kernel_size=25,
            cell_size=10
        )
        
        # Imobilidade (X, Y, Timestamp)
        self.track_history = {} # ID: { x, y, timestamp_start }
        self.immobility_threshold = immobility_threshold
        self.immobility_time_sec = immobility_time_sec
        self.dead_or_sick_ids = set()
        
        self.logger.info("Engrenagem de Comportamento e Heatmap Inicializada.")

    def update_immobility_and_get_alerts(self, detections):
        """
        Analisa as detecções, calcula a distância de imobilidade e retorna IDs anômalos.
        """
        alerts = []
        current_time = time.time()
        
        if detections is None or len(detections) == 0:
            return alerts
            
        for i in range(len(detections)):
            if detections.tracker_id is None:
                continue
                
            track_id = int(detections.tracker_id[i])
            box = detections.xyxy[i]
            
            # Centroide
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0
            
            if track_id not in self.track_history:
                self.track_history[track_id] = {
                    'x': cx, 'y': cy, 'ts': current_time, 'last_seen': current_time
                }
            else:
                hist = self.track_history[track_id]
                dist = math.hypot(cx - hist['x'], cy - hist['y'])
                
                # Se moveu mais que o threshold, reseta o tempo e a âncora
                if dist > self.immobility_threshold:
                    hist['x'] = cx
                    hist['y'] = cy
                    hist['ts'] = current_time
                    if track_id in self.dead_or_sick_ids:
                        self.dead_or_sick_ids.remove(track_id)
                else:
                    # Imóvel. Há quanto tempo?
                    time_inactive = current_time - hist['ts']
                    if time_inactive > self.immobility_time_sec and track_id not in self.dead_or_sick_ids:
                        self.dead_or_sick_ids.add(track_id)
                        alerts.append(f"ALERTA: Ave ID {track_id} inativa há {int(time_inactive)}s.")
                        
                hist['last_seen'] = current_time

        # Cleanup: remover IDs que não são vistos há tempão (ex: 60s)
        ids_to_del = [tid for tid, data in self.track_history.items() if (current_time - data['last_seen']) > 60.0]
        for tid in ids_to_del:
            del self.track_history[tid]
            if tid in self.dead_or_sick_ids:
                 self.dead_or_sick_ids.remove(tid)
                 
        return alerts

    def annotate_heatmap(self, frame, detections):
        """
        Aplica o mapa de calor no frame cru
        """
        if detections is None or len(detections) == 0:
            return frame
        return self.heatmap_annotator.annotate(scene=frame, detections=detections)
