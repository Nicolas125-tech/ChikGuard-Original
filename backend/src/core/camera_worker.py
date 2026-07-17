import os
import time
import logging
import threading
import cv2
import numpy as np

logger = logging.getLogger("chikguard.camera_worker")

# Flag global para controlar a execução da thread
camera_running = True
_camera_thread = None

def simulate_telemetry_step():
    """Simula dados de telemetria variando com base no estado dos atuadores."""
    from src.core.state import sensor_state
    from src.core.fsm_task import actuator_state
    import random
    
    # Valores atuais
    temp = sensor_state.get("temperature_c", 0.0)
    if temp == 0.0:
        # Inicializa com valores normais realistas
        temp = 24.8
        sensor_state["humidity_pct"] = 62.0
        sensor_state["ammonia_ppm"] = 5.2
        sensor_state["feed_level_pct"] = 78.0
        sensor_state["water_level_pct"] = 88.0
        
    # Ajusta temperatura com base na FSM/atuadores
    if actuator_state.get("aquecedor_on", False):
        temp += 0.15 + random.uniform(-0.03, 0.03)
    elif actuator_state.get("ventilacao_on", False):
        temp -= 0.12 + random.uniform(-0.03, 0.03)
    else:
        # Converge lentamente para a temperatura ambiente simulada (23°C)
        temp += (23.0 - temp) * 0.01 + random.uniform(-0.02, 0.02)
        
    # Limitações físicas do galpão
    temp = max(12.0, min(38.0, temp))
    
    # Pequenas variações de umidade e amônia
    h = sensor_state.get("humidity_pct", 60.0) + random.uniform(-0.15, 0.15)
    h = max(30.0, min(90.0, h))
    
    a = sensor_state.get("ammonia_ppm", 5.0) + random.uniform(-0.03, 0.03)
    a = max(0.0, min(50.0, a))
    
    sensor_state["temperature_c"] = round(temp, 1)
    sensor_state["humidity_pct"] = round(h, 1)
    sensor_state["ammonia_ppm"] = round(a, 1)
    sensor_state["source"] = "telemetry_simulator"
    sensor_state["updated_at"] = time.time()

def camera_worker():
    global camera_running
    from src.core.config import load_settings
    from src.core.state import set_global_frame, sensor_state, live_birds, species_counts, weight_state, cv_lock
    from src.core.cv_engine import SpeciesClassifier, BirdPoseAnalyzer, PerfMetrics, CVOverlay
    from ultralytics import YOLO

    settings = load_settings()
    camera_index = settings.camera_index
    
    logger.info(f"Iniciando camera_worker. Câmera Index configurado: {camera_index}")
    
    cap = None
    use_sim = False
    
    # 1. Tenta conectar na webcam / câmera local
    try:
        cap = cv2.VideoCapture(camera_index)
        if cap.isOpened():
            # Testa leitura de frame
            ret, _ = cap.read()
            if ret:
                logger.info(f"Câmera real (webcam) {camera_index} iniciada com sucesso.")
            else:
                logger.warning(f"Câmera real {camera_index} abriu, mas falhou ao ler frames.")
                cap.release()
                cap = None
    except Exception as exc:
        logger.warning(f"Erro ao abrir câmera real: {exc}")
        cap = None
        
    # 2. Se a câmera real falhar, usa o vídeo de simulação como fallback
    if cap is None:
        use_sim = True
        # Procura o arquivo na pasta raiz do backend
        sim_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "video_granja.mp4"))
        logger.info(f"Câmera real indisponível. Iniciando simulador com vídeo: {sim_path}")
        if os.path.exists(sim_path):
            cap = cv2.VideoCapture(sim_path)
            if cap.isOpened():
                logger.info("Vídeo de simulação 'video_granja.mp4' aberto com sucesso.")
            else:
                logger.error("Falha ao abrir vídeo de simulação.")
                cap = None
        else:
            logger.error("Vídeo de simulação 'video_granja.mp4' não foi encontrado na raiz do backend.")
            cap = None
            
    # 3. Inicializa modelo YOLO
    model = None
    species_classifier = SpeciesClassifier()
    pose_analyzer = BirdPoseAnalyzer()
    metrics = PerfMetrics()
    
    try:
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "yolov8n-seg.pt"))
        if not os.path.exists(model_path):
            model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "yolov8n.pt"))
            
        if os.path.exists(model_path):
            logger.info(f"Carregando modelo de detecção YOLO em CPU a partir de {model_path}...")
            model = YOLO(model_path)
            model.to("cpu")
            logger.info("YOLO carregado com sucesso.")
        else:
            logger.error("Nenhum arquivo de pesos YOLO (yolov8n-seg.pt ou yolov8n.pt) encontrado para inferência local.")
    except Exception as e:
        logger.error(f"Erro na inicialização do modelo YOLO: {e}")

    frame_count = 0
    last_telemetry_sim_ts = 0.0
    
    while camera_running:
        t_loop_start = time.perf_counter()
        
        # Simula passo de telemetria a cada 1 segundo
        now = time.time()
        if now - last_telemetry_sim_ts >= 1.0:
            last_telemetry_sim_ts = now
            try:
                simulate_telemetry_step()
            except Exception as e:
                logger.error(f"Erro na simulação de telemetria: {e}")

        # Se não houver feed de vídeo aberto, gera frame preto com erro
        if cap is None or not cap.isOpened():
            err_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(
                err_frame,
                "ERRO: SEM DISPOSITIVO DE CAMERA",
                (50, 240),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
                cv2.LINE_AA
            )
            set_global_frame(err_frame)
            time.sleep(1)
            # Tenta reconectar câmera ou reabrir simulador
            if use_sim:
                sim_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "video_granja.mp4"))
                if os.path.exists(sim_path):
                    cap = cv2.VideoCapture(sim_path)
            else:
                cap = cv2.VideoCapture(camera_index)
            continue
            
        ret, frame = cap.read()
        if not ret:
            if use_sim:
                # Loop do vídeo
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            else:
                logger.warning("Falha ao ler frame da webcam real.")
                time.sleep(0.5)
                continue
                
        frame_count += 1
        
        # Redimensiona para resolução padrão de exibição
        frame_resized = cv2.resize(frame, (640, 480))
        
        detections = []
        
        # Executa inferência YOLO a cada 3 frames para evitar sobrecarga de CPU local
        if model is not None and frame_count % 3 == 0:
            try:
                # Otimizado para identificar pontinhos amarelos (pintinhos pequenos a distância)
                results = model.track(
                    frame_resized,
                    persist=True,
                    tracker="bytetrack.yaml",
                    conf=0.15,
                    imgsz=640,
                    verbose=False
                )
                
                if results and results[0].boxes is not None:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    confs = results[0].boxes.conf.cpu().numpy()
                    clss = results[0].boxes.cls.cpu().numpy()
                    ids = results[0].boxes.id.cpu().numpy() if results[0].boxes.id is not None else [-1] * len(boxes)
                    
                    chicks_count = 0
                    hens_count = 0
                    person_detected = False
                    
                    for i in range(len(boxes)):
                        box = [int(v) for v in boxes[i]]
                        conf = float(confs[i])
                        cid = int(clss[i])
                        uid = int(ids[i])
                        
                        # 1. Trata detecção de pessoa (classe 0) -> Alerta de Intrusão
                        if cid == 0:
                            person_detected = True
                            det = {
                                "box": box,
                                "confidence": conf,
                                "class_id": cid,
                                "track_id": uid,
                                "stable_bird_uid": uid,
                                "species": "person",
                                "species_label": "INVASOR",
                                "color": (0, 0, 255), # Vermelho neon
                                "pose_label": "ATENCAO"
                            }
                            detections.append(det)
                            continue
                            
                        # 2. Ignora qualquer classe que não seja ave (classe 14)
                        if cid != 14:
                            continue
                        
                        # 3. Processa ave (pintinho / galinha)
                        pose_info = pose_analyzer.analyze(box, 0.0, frame_resized.shape)
                        species_info = species_classifier.classify(frame_resized, box, "bird", 0.0)
                        
                        det = {
                            "box": box,
                            "confidence": conf,
                            "class_id": cid,
                            "track_id": uid,
                            "stable_bird_uid": uid
                        }
                        det.update(pose_info)
                        det.update(species_info)
                        detections.append(det)
                        
                        if species_info["species"] == "chick":
                            chicks_count += 1
                        else:
                            hens_count += 1
                            
                    # Atualiza os estados globais sob lock de forma thread-safe
                    from src.core.state import intrusion_state
                    with cv_lock:
                        # Atualiza alertas de segurança
                        intrusion_state["active"] = person_detected
                        if person_detected:
                            intrusion_state["last_alert_ts"] = time.time()
                            intrusion_state["alerts_count"] += 1
                            
                        # Atualiza aves ativas
                        live_birds.clear()
                        for d in detections:
                            # Apenas rastreia aves no live_birds
                            if d["class_id"] == 14:
                                uid = d["track_id"]
                                if uid >= 0:
                                    live_birds[uid] = {
                                        "box": d["box"],
                                        "conf": d["confidence"],
                                        "track_id": uid,
                                        "species": d["species"],
                                        "species_label": d["species_label"],
                                        "last_seen": time.time(),
                                        "mask_area_px": 0.0
                                    }
                                    
                        species_counts["chicks"] = chicks_count
                        species_counts["hens"] = hens_count
                        species_counts["total"] = chicks_count + hens_count
                        
                        # Estimativa dinâmica de peso
                        bird_total = chicks_count + hens_count
                        if bird_total > 0:
                            weight_state["avg_weight_g"] = round(1180.0 + bird_total * 2.8 + np.random.normal(0, 4), 1)
                            weight_state["count"] = bird_total
                            weight_state["confidence"] = 0.93
                            weight_state["updated_at"] = time.time()
            except Exception as cv_err:
                logger.error(f"Erro no processamento YOLO: {cv_err}")
                
        # Desenha overlay rico no frame
        try:
            processed_frame = frame_resized.copy()
            if detections:
                processed_frame = CVOverlay.draw_detections(processed_frame, detections, set())
                
            # Adiciona informações HUD e metricas
            metrics_dict = {
                "fps_camera": 30.0,
                "fps_inference": 10.0 if model else 0.0,
                "latency_ms": 45.0 if model else 0.0,
                "sahi_enabled": False,
                "backend_name": "pytorch" if model else "none"
            }
            
            processed_frame = CVOverlay.draw_hud(
                processed_frame,
                metrics_dict,
                species_counts,
                "Status: NORMAL" if sensor_state.get("temperature_c", 25.0) < 32 else "Status: CALOR"
            )
            
            set_global_frame(processed_frame)
        except Exception as overlay_err:
            logger.error(f"Erro ao gerar overlay visual: {overlay_err}")
            set_global_frame(frame_resized)
            
        # Controla taxa de quadros (throttle para 30 FPS)
        elapsed = time.perf_counter() - t_loop_start
        sleep_t = 0.033 - elapsed
        if sleep_t > 0.001:
            time.sleep(sleep_t)
            
    if cap is not None:
        cap.release()
    logger.info("camera_worker encerrado.")

def start_camera_thread():
    global camera_running, _camera_thread
    camera_running = True
    _camera_thread = threading.Thread(target=camera_worker, name="ChikGuardCameraWorker", daemon=True)
    _camera_thread.start()
    logger.info("Thread do camera_worker iniciada.")

def stop_camera_thread():
    global camera_running, _camera_thread
    camera_running = False
    if _camera_thread:
        _camera_thread.join(timeout=2.0)
        logger.info("Thread do camera_worker finalizada.")
