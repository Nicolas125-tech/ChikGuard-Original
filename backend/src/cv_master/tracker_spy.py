import logging

try:
    import supervision as sv
except ImportError:
    pass

class SpyTracker:
    def __init__(self, track_activation_threshold=0.40, lost_track_buffer=90):
        """
        Tracker Multi-alvo utilizando ByteTrack.
        O lost_track_buffer é maximizado para resistir a longas oclusões.
        """
        self.logger = logging.getLogger("cv_master.SpyTracker")
        self.logger.info("Inicializando ByteTrack Anti-Flicker (Spy Level)...")
        self.tracker = sv.ByteTrack(
            track_activation_threshold=track_activation_threshold,
            lost_track_buffer=lost_track_buffer,
            minimum_matching_threshold=0.8,
            frame_rate=30
        )
        
    def update(self, detections):
        """
        Atualiza o estado do Tracker e injeta os Tracker IDs na classe sv.Detections.
        """
        # Filtra as de baixíssima confiança apenas pro tracker
        tracked_detections = self.tracker.update_with_detections(detections=detections)
        return tracked_detections
