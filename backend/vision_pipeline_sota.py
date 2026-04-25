import os
import cv2
import time
import logging
import threading
from src.cv_master.inference_sota import SOTAInferenceEngine
from src.cv_master.tracker_spy import SpyTracker
from src.cv_master.behavior_engine import BehaviorEngine
from src.cv_master.stream_gateway import HLSStreamGateway
from core.cv_engine import VideoCaptureThread # reaproveitando thread de buffer zero

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class SOTAPipeline:
    def __init__(self, src=0, model_path="yolov8n-seg.pt"):
        self.logger = logging.getLogger("SOTAPipeline")
        self.video_src = src
        self.stream = None
        
        # 1. Inference Engine
        self.inference = SOTAInferenceEngine(model_path=model_path, confidence=0.45)
        
        # 2. Advanced Tracking
        self.tracker = SpyTracker(track_activation_threshold=0.45, lost_track_buffer=90)
        
        # 3. Behavior Constraints
        self.behavior = BehaviorEngine(immobility_threshold=15.0, immobility_time_sec=120)
        
        # 4. HLS Stream Gateway
        self.stream_gateway = HLSStreamGateway(fps=30)
        
        # Annotators (Supervision)
        import supervision as sv
        self.box_annotator = sv.BoxAnnotator(thickness=2)
        self.label_annotator = sv.LabelAnnotator(text_scale=0.5, text_padding=5)
        
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        # We need to use OpenCV or VideoCaptureThread to get frames
        cap = cv2.VideoCapture(self.video_src)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        
        if not cap.isOpened():
            self.logger.error("Falha ao abrir stream de vídeo.")
            return

        # Start FFmpeg Stream Processor
        # Width/height must match frame shape
        ret, first_frame = cap.read()
        if not ret:
            return
        
        frame_h, frame_w = first_frame.shape[:2]
        self.stream_gateway.start_pipeline(width=frame_w, height=frame_h)
        
        self.logger.info("Pipeline SOTA Iniciado. Streaming HLS ativo.")
        
        try:
            while self.running:
                start_time = time.perf_counter()
                
                ret, frame = cap.read()
                if not ret or frame is None:
                    # Restart video if file
                    if isinstance(self.video_src, str) and self.video_src.endswith(".mp4"):
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        break
                
                # 1. SAHI Inference SOTA
                detections = self.inference.process_frame(frame, slice_size=640)
                
                # 2. Spy Tracker
                tracked = self.tracker.update(detections)
                
                # 3. Behavior Analysis
                alerts = self.behavior.update_immobility_and_get_alerts(tracked)
                for alert in alerts:
                    self.logger.warning(alert)
                    # AQUI PODERÍAMOS DISPARAR WEBSOCKET SOCKETIO
                
                # 4. Render
                annotated = frame.copy()
                labels = []
                for i in range(len(tracked)):
                    tracker_id = tracked.tracker_id[i]
                    conf = tracked.confidence[i]
                    labels.append(f"#{tracker_id} {conf:.2f}")

                annotated = self.box_annotator.annotate(scene=annotated, detections=tracked)
                annotated = self.label_annotator.annotate(scene=annotated, detections=tracked, labels=labels)
                
                # Aquece com o mapa de calor vetorial
                annotated = self.behavior.annotate_heatmap(annotated, tracked)
                
                # Exibir FPS e Contagem Otimizada na Tela
                fps = 1.0 / (time.perf_counter() - start_time)
                cv2.putText(annotated, f"Aves: {len(tracked)} | FPS: {fps:.1f}", (20, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                
                if self.behavior.dead_or_sick_ids:
                    cv2.putText(annotated, f"ANOMALIAS DETECTADAS: {len(self.behavior.dead_or_sick_ids)}", 
                                (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                
                # Envia via Pipes pro HLS Server
                self.stream_gateway.push_frame(annotated)
                
        except Exception as e:
            self.logger.exception(f"Erro no Kernel SOTA: {e}")
        finally:
            cap.release()
            self.stream_gateway.stop_pipeline()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

if __name__ == "__main__":
    VIDEO_SOURCE = "video_granja.mp4"
    pipeline = SOTAPipeline(src=VIDEO_SOURCE)
    pipeline.start()
    
    # Mantem rodando para que os pipes HLS fluam livremente no Flask (Simulado)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pipeline.stop()
        print("SOTA Pipeline Encerrado Cortêsmente.")
