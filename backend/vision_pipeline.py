import cv2
import time
import numpy as np
import threading
import queue
import logging

try:
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    import supervision as sv
    # Utilizaremos a biblioteca supervision que implementa um ByteTrack nativo e perfeitamente
    # integrado aos outputs do SAHI de maneira limpa, mantendo a consistência dos IDs.
except ImportError:
    print("ERRO: Bibliotecas críticas ausentes.")
    print("Instale usando: pip install sahi ultralytics supervision opencv-python")
    exit(1)

# ==========================================
# 1. CALIBRAÇÃO DE PARÂMETROS E CONFIGURAÇÕES
# ==========================================
# Parâmetros focados em estabilidade e contagem sem Flickering
CONFIDENCE_THRESHOLD = 0.45  # Confiança mínima para aceitar uma detecção
IOU_THRESHOLD = 0.50         # Overlap máximo permitido (ajuda a separar frangos aglomerados)
TRACK_BUFFER = 60            # Tolerância do ByteTrack à oclusão (em frames). Impede que o ID limpe instantaneamente ao se esconder.

# Parâmetros do SAHI (Slicing) - FUNDAMENTAL para aves pequenas e distantes
# A lógica de fatiamento corta a resolução 1080p/4K em janelas menores.
SLICE_HEIGHT = 640
SLICE_WIDTH = 640
OVERLAP_RATIO = 0.20         # 20% de transição entre fatias garante que uma ave dividida na borda seja detectada corretamente.

# Configuração Edge (Mini PC Linux / TensorRT / OpenVINO)
MODEL_PATH = "yolov8n-seg.pt"  # Altere para .engine (TensorRT) ou openvino_model/ (OpenVINO) no ambiente de produção
MODEL_TYPE = "yolov8"
MODEL_DEVICE = "cuda:0"      # Use 'cpu' para OpenVINO puro se não usar a GPU, 'cuda:0' para NVIDIA

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ==========================================
# 2. CAPTURA ASSÍNCRONA (Hardware Constraints)
# ==========================================
class VideoCaptureThread:
    """
    Thread dedicada para limpar o buffer da câmera, extraindo frames em zero-latency.
    Isso impede que gargalos de processamento atrasem o fluxo nativo da câmera.
    """
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        if not self.cap.isOpened():
            raise RuntimeError(f"Falha ao abrir a fonte de vídeo: {src}")
            
        self.q = queue.Queue(maxsize=3) # Limitamos rigidamente o tamanho da fila
        self.running = True
        self.thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.thread.start()
        
    def _reader_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                logging.warning("Falha na captura do frame da câmera (Stream interrompido ou Fim do Vídeo).")
                self.running = False
                break
            
            # Se a fila estiver cheia, descarta o frame mais antigo (zero-delay buffer)
            if not self.q.empty():
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    pass
            self.q.put(frame)

    def read(self):
        try:
            return True, self.q.get(timeout=2)
        except queue.Empty:
            return False, None
            
    def release(self):
        self.running = False
        self.thread.join()
        self.cap.release()

# ==========================================
# 3. PIPELINE DE INFERÊNCIA COGNITIVA
# ==========================================
class VisionPipeline:
    def __init__(self, src=0):
        self.video_src = src
        self.stream = None
        
        logging.info("Carregando modelo segmentador Edge via SAHI...")
        self.detection_model = AutoDetectionModel.from_pretrained(
            model_type=MODEL_TYPE,
            model_path=MODEL_PATH,
            confidence_threshold=CONFIDENCE_THRESHOLD,
            device=MODEL_DEVICE,  # OOTB suporta acelerações delegadas pelo backend Ultralytics
        )
        # Força o threshold de IOU diretamente nas args que o AutoDetectionModel passará
        self.detection_model.engine.model.iou = IOU_THRESHOLD

        logging.info("Inicializando o rastreador ByteTrack...")
        # ByteTrack adaptativo: lida muito bem com ruídos de detecção de pequenos objetos.
        self.tracker = sv.ByteTrack(
            track_activation_threshold=CONFIDENCE_THRESHOLD,
            lost_track_buffer=TRACK_BUFFER,
            minimum_matching_threshold=0.8,
            frame_rate=30
        )
        
        # Anotadores Visuais (Rostos dos pintinhos)
        self.box_annotator = sv.BoundingBoxAnnotator(thickness=2)
        self.mask_annotator = sv.MaskAnnotator(opacity=0.5)
        self.label_annotator = sv.LabelAnnotator(text_scale=0.5, text_padding=5)

    def run(self):
        logging.info(f"Iniciando thread da câmera na fonte: {self.video_src}")
        self.stream = VideoCaptureThread(self.video_src)
        time.sleep(1.0) # Aquece a câmera e enche a fila
        
        frame_counter = 0
        total_fps_time = 0
        
        try:
            while True:
                start_time = time.perf_counter()
                
                ret, frame = self.stream.read()
                if not ret or frame is None:
                    logging.info("Fim da stream. Encerrando o pipeline.")
                    break
                
                # ==============================================
                # 3.1. Inferência com Fatiamento SAHI
                # ==============================================
                # get_sliced_prediction processa um frame gigante por partes (512x512/640x640)
                # re-unindo as detecções e os segmentos com Non-Maximum Suppression (NMS)
                result = get_sliced_prediction(
                    frame,
                    self.detection_model,
                    slice_height=SLICE_HEIGHT,
                    slice_width=SLICE_WIDTH,
                    overlap_height_ratio=OVERLAP_RATIO,
                    overlap_width_ratio=OVERLAP_RATIO,
                    postprocess_class_agnostic=True, # Evita NMS desnecessário se houver multi-classes coladas
                    postprocess_match_metric="IOU"
                )

                # ==============================================
                # 3.2. Ponte SAHI -> Supervision (Detecções e Máscaras)
                # ==============================================
                # O Supervision converte o ObjectPredictionList do SAHI no formato Detections arrayizado,
                # suportando extração nativa das máscaras preditas do YOLO Seg.
                detections = sv.Detections.from_sahi(result)

                # Opcional: Remover detecções anômalas gigantes (ex: tratadores em vez de frangos) usando área
                # detections = detections[(detections.area < 100000) & (detections.area > 50)]

                # ==============================================
                # 3.3. Estabilidade e Contagem com Tracking
                # ==============================================
                # O ByteTrack atua nas caixas e confianças, mas o tracker supervision repassa o índice 
                # mantendo as máscaras linkadas com o tracker ID gerado. Zero flickr. 
                tracked_detections = self.tracker.update_with_detections(detections=detections)

                # ==============================================
                # 3.4. Anotações Visuais
                # ==============================================
                annotated_frame = frame.copy()
                labels = []
                
                for i in range(len(tracked_detections)):
                    # tracked_detections armazena conf, class_id e tracker_id
                    tracker_id = tracked_detections.tracker_id[i]
                    confidence = tracked_detections.confidence[i]
                    labels.append(f"#{tracker_id} {confidence:.2f}")

                # Aplica as overlays gráficas (Mascaras + Caixas + IDs)
                annotated_frame = self.mask_annotator.annotate(scene=annotated_frame, detections=tracked_detections)
                annotated_frame = self.box_annotator.annotate(scene=annotated_frame, detections=tracked_detections)
                annotated_frame = self.label_annotator.annotate(scene=annotated_frame, detections=tracked_detections, labels=labels)

                # Controle de Desempenho e Log Visual
                end_time = time.perf_counter()
                fps = 1.0 / (end_time - start_time)
                total_fps_time += fps
                frame_counter += 1
                
                # Exibição de Resumo em Tela
                num_aves = len(tracked_detections)
                cv2.putText(annotated_frame, f"Aves: {num_aves} | FPS: {fps:.1f}", (20, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)

                cv2.imshow("Supervision CV - Industrial Monitor", annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            logging.info("Interrupção solicitada pelo usuário.")
        finally:
            self.stream.release()
            cv2.destroyAllWindows()
            if frame_counter > 0:
                avg_fps = total_fps_time / frame_counter
                logging.info(f"Pipeline finalizado. FPS médio: {avg_fps:.2f}")

if __name__ == "__main__":
    # Inicia o pipeline de visão. Em produção, substitua a string pelo ID da stream RTMP ou Câmera.
    VIDEO_SOURCE = "video_granja.mp4" # ou 0 para USB Webcam Local
    pipeline = VisionPipeline(src=VIDEO_SOURCE)
    pipeline.run()
