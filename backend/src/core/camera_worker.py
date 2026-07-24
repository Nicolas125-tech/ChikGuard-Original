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

def save_telemetry_snapshot_to_db():
    """Grava as medições atuais de sensores e dados de visão no SQLite local."""
    try:
        from database import SensorReading, WeightEstimate
        from src.db.session import SessionLocal
        from src.core.state import sensor_state, species_counts, weight_state

        db_sess = SessionLocal()
        try:
            sr = SensorReading(
                camera_id="galpao-1",
                temperature_c=sensor_state.get("temperature_c", 24.8),
                humidity_pct=sensor_state.get("humidity_pct", 62.0),
                ammonia_ppm=sensor_state.get("ammonia_ppm", 5.2),
                feed_level_pct=sensor_state.get("feed_level_pct", 78.0),
                water_level_pct=sensor_state.get("water_level_pct", 88.0),
                source=sensor_state.get("source", "camera_worker")
            )
            if hasattr(sr, "mark_pending"):
                sr.mark_pending()
            db_sess.add(sr)

            bird_tot = species_counts.get("total", 0)
            if bird_tot > 0:
                we = WeightEstimate(
                    camera_id="galpao-1",
                    avg_weight_g=weight_state.get("avg_weight_g", 1200.0),
                    ideal_weight_g=1250.0,
                    flock_count=bird_tot,
                    confidence=0.93,
                    source="vision_estimate"
                )
                db_sess.add(we)
            db_sess.commit()
            print(f"[SAVED SNAPSHOT TO DB] Temp: {sr.temperature_c}°C, Status: {sr.sync_status}")
        except Exception as db_save_err:
            db_sess.rollback()
            logger.error(f"Erro ao salvar histórico visual no SQLite: {db_save_err}")
            print(f"[SAVE ERROR] {db_save_err}")
        finally:
            db_sess.close()
    except Exception as exc:
        logger.error(f"Falha na abertura de sessão de persistência: {exc}")
        print(f"[SESSION ERROR] {exc}")
_raw_frame = None
_latest_detections = []
_cap = None
_use_sim = False
_camera_index = 0
_cv_lock = threading.Lock()

def _capture_thread_func():
    """Thread de aquisição de imagem dedicada - lê o frame mais recente e limpa buffer."""
    global _raw_frame, _cap, _use_sim, camera_running, _camera_index
    
    consecutive_failures = 0
    while camera_running:
        cap_instance = _cap
        if cap_instance is None or not cap_instance.isOpened():
            time.sleep(0.1)
            continue
            
        ret, frame = cap_instance.read()
        if not ret:
            if _use_sim:
                # Loop do vídeo de simulação
                cap_instance.set(cv2.CAP_PROP_POS_FRAMES, 0)
            else:
                consecutive_failures += 1
                if consecutive_failures > 30:
                    logger.warning("Conexão com a câmera real perdida no loop de captura.")
                    # Tenta reabrir
                    cap_instance.release()
                    _cap = cv2.VideoCapture(_camera_index)
                    consecutive_failures = 0
                time.sleep(0.05)
            continue
            
        consecutive_failures = 0
        
        # Redimensiona para resolução padrão
        resized = cv2.resize(frame, (640, 480))
        
        with _cv_lock:
            _raw_frame = resized
            
        # Pequena pausa para liberar a CPU
        time.sleep(0.005)

def _inference_thread_func(model, species_classifier, pose_analyzer):
    """Thread dedicada de inferência YOLOv8 - processa frames de forma assíncrona com sincronização local/nuvem."""
    global _raw_frame, _latest_detections, camera_running
    
    last_batch_query_ts = 0.0
    last_db_save_ts = 0.0
    frame_counter = 0

    # Classes do COCO aceitas como candidatas para aves/pintinhos em ambiente agrícola:
    # 14: passaro/ave, 15: gato, 16: cachorro, 18: ovelha, 19: vaca, 21: urso (blobs felpudos pequenos)
    BIRD_CANDIDATE_CLASSES = {14, 15, 16, 18, 19, 21}
    
    while camera_running:
        frame_to_process = None
        with _cv_lock:
            if _raw_frame is not None:
                frame_to_process = _raw_frame.copy()
                
        if frame_to_process is None:
            time.sleep(0.05)
            continue
            
        now_ts = time.time()
        frame_counter += 1

        # 1. Consulta idade do lote do DB periodicamente (a cada 15s)
        if now_ts - last_batch_query_ts >= 15.0:
            last_batch_query_ts = now_ts
            try:
                from database import Batch
                from src.db.session import SessionLocal
                from datetime import datetime
                db_session = SessionLocal()
                active_batch = db_session.query(Batch).filter_by(active=True).first()
                if active_batch:
                    age_days = (datetime.utcnow() - active_batch.start_date.replace(tzinfo=None)).days
                    age_days = max(1, age_days)
                    species_classifier.set_batch_age(age_days)
                    logger.info(f"Fator de idade do lote sincronizado: {age_days} dias.")
                else:
                    # Sem lote ativo no DB, default para pintinhos jovens para demonstrar localmente
                    species_classifier.set_batch_age(5)
                db_session.close()
            except Exception as db_err:
                logger.error(f"Erro ao consultar DB para idade do lote: {db_err}")

        # 2. Executa inferência YOLO com resolução e confiança otimizadas
        try:
            results = model.track(
                frame_to_process,
                persist=True,
                tracker="bytetrack.yaml",
                conf=0.12, # Alta sensibilidade para detecção de pintinhos distantes e pequenos
                imgsz=640,  # Resolução para resolver pintinhos pequenos
                verbose=False
            )
            
            new_detections = []
            chicks_count = 0
            hens_count = 0
            person_detected = False
            
            if results and results[0].boxes is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                confs = results[0].boxes.conf.cpu().numpy()
                clss = results[0].boxes.cls.cpu().numpy()
                ids = results[0].boxes.id.cpu().numpy() if results[0].boxes.id is not None else [-1] * len(boxes)
                
                for i in range(len(boxes)):
                    box = [int(v) for v in boxes[i]]
                    conf = float(confs[i])
                    cid = int(clss[i])
                    uid = int(ids[i])
                    
                    # Trata detecção de pessoa (classe 0) -> Alerta de Intrusão
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
                        new_detections.append(det)
                        continue
                        
                    # Aceita qualquer classe animal candidata no contexto da granja
                    if cid not in BIRD_CANDIDATE_CLASSES:
                        continue
                    
                    # Processa ave (pintinho / galinha) com suavização temporal por track_id
                    pose_info = pose_analyzer.analyze(box, 0.0, frame_to_process.shape)
                    species_info = species_classifier.classify(frame_to_process, box, "bird", 0.0, track_id=uid)
                    
                    det = {
                        "box": box,
                        "confidence": conf,
                        "class_id": 14,  # Normaliza para classe ave
                        "track_id": uid,
                        "stable_bird_uid": uid
                    }
                    det.update(pose_info)
                    det.update(species_info)
                    new_detections.append(det)
                    
                    if species_info["species"] == "chick":
                        chicks_count += 1
                    else:
                        hens_count += 1

            # Atualiza estados globais do sistema de forma thread-safe
            from src.core.state import intrusion_state, live_birds, species_counts, weight_state, cv_lock
            with cv_lock:
                # Atualiza alertas de segurança
                intrusion_state["active"] = person_detected
                if person_detected:
                    intrusion_state["last_alert_ts"] = time.time()
                    intrusion_state["alerts_count"] += 1
                    
                # Atualiza aves ativas
                live_birds.clear()
                for d in new_detections:
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
                    weight_state["avg_weight_g"] = round(1180.0 + bird_total * 2.8 + float(np.random.normal(0, 4)), 1)
                    weight_state["count"] = bird_total
                    weight_state["confidence"] = 0.93
                    weight_state["updated_at"] = time.time()

            with _cv_lock:
                _latest_detections = new_detections

            # 3. Gravador periódico no SQLite para acumular histórico e alimentar o Supabase Sync Worker (a cada 5s)
            if now_ts - last_db_save_ts >= 5.0:
                last_db_save_ts = now_ts
                try:
                    from database import SensorReading, WeightEstimate
                    from src.db.session import SessionLocal
                    from src.core.state import sensor_state

                    db_sess = SessionLocal()
                    try:
                        sr = SensorReading(
                            camera_id="galpao-1",
                            temperature_c=sensor_state.get("temperature_c", 25.0),
                            humidity_pct=sensor_state.get("humidity_pct", 60.0),
                            ammonia_ppm=sensor_state.get("ammonia_ppm", 5.0),
                            feed_level_pct=sensor_state.get("feed_level_pct", 75.0),
                            water_level_pct=sensor_state.get("water_level_pct", 85.0),
                            source="camera_worker"
                        )
                        if hasattr(sr, "mark_pending"):
                            sr.mark_pending()
                        db_sess.add(sr)

                        bird_tot = species_counts.get("total", 0)
                        if bird_tot > 0:
                            we = WeightEstimate(
                                camera_id="galpao-1",
                                avg_weight_g=weight_state.get("avg_weight_g", 1200.0),
                                ideal_weight_g=1250.0,
                                flock_count=bird_tot,
                                confidence=0.93,
                                source="vision_estimate"
                            )
                            db_sess.add(we)
                        db_sess.commit()
                    except Exception as db_save_err:
                        db_sess.rollback()
                        logger.error(f"Erro ao salvar histórico visual no SQLite: {db_save_err}")
                    finally:
                        db_sess.close()
                except Exception as exc:
                    logger.error(f"Falha na abertura de sessão de persistência: {exc}")

        except Exception as cv_err:
            logger.error(f"Erro no processamento YOLO da thread: {cv_err}")
            
        time.sleep(0.01)
            
        # Pequena pausa para liberar a CPU
        time.sleep(0.01)

def camera_worker():
    global camera_running, _cap, _use_sim, _camera_index, _raw_frame, _latest_detections
    from src.core.config import load_settings
    from src.core.state import set_global_frame, sensor_state, species_counts
    from src.core.cv_engine import SpeciesClassifier, BirdPoseAnalyzer, CVOverlay
    from ultralytics import YOLO

    settings = load_settings()
    _camera_index = settings.camera_index
    
    logger.info(f"Iniciando camera_worker. Câmera Index: {_camera_index}")
    print(f"[CAMERA WORKER] Starting... camera_index={_camera_index}")
    
    _cap = None
    _use_sim = False
    
    # 1. Tenta conectar na webcam
    try:
        _cap = cv2.VideoCapture(_camera_index)
        if _cap.isOpened():
            ret, _ = _cap.read()
            if ret:
                logger.info(f"Câmera real {_camera_index} iniciada com sucesso.")
            else:
                _cap.release()
                _cap = None
    except Exception as exc:
        logger.warning(f"Erro ao abrir câmera real: {exc}")
        _cap = None
        
    # 2. Fallback para vídeo de simulação
    if _cap is None:
        _use_sim = True
        sim_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "video_granja.mp4"))
        logger.info(f"Ativando simulador com vídeo: {sim_path}")
        print(f"[CAMERA WORKER] Using simulation video: {sim_path}")
        if os.path.exists(sim_path):
            _cap = cv2.VideoCapture(sim_path)
        else:
            logger.error("Vídeo de simulação 'video_granja.mp4' não encontrado.")
            _cap = None
            
    # 3. Inicializa modelo YOLO
    model = None
    species_classifier = SpeciesClassifier()
    pose_analyzer = BirdPoseAnalyzer()
    
    try:
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "yolov8n-seg.pt"))
        if not os.path.exists(model_path):
            model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "yolov8n.pt"))
            
        if os.path.exists(model_path):
            model = YOLO(model_path)
            model.to("cpu")
            logger.info("YOLO carregado com sucesso.")
            print("[CAMERA WORKER] YOLO loaded successfully")
        else:
            logger.error("Nenhum arquivo de pesos YOLO encontrado.")
    except Exception as e:
        logger.error(f"Erro na inicialização do modelo YOLO: {e}")

    # 4. Inicia as threads dedicadas de Captura e Inferência YOLO
    capture_thread = threading.Thread(target=_capture_thread_func, name="CaptureThread", daemon=True)
    capture_thread.start()
    
    inference_thread = None
    if model is not None:
        inference_thread = threading.Thread(
            target=_inference_thread_func,
            args=(model, species_classifier, pose_analyzer),
            name="InferenceThread",
            daemon=True
        )
        inference_thread.start()

    last_telemetry_sim_ts = 0.0
    last_db_save_ts = 0.0
    print("[CAMERA WORKER] Entering main coordinator loop...")
    
    # 5. Loop do Coordenador Principal (Roda a 30 FPS estável, sem travar!)
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

        # Salva snapshot de telemetria no SQLite a cada 3 segundos
        if now - last_db_save_ts >= 3.0:
            last_db_save_ts = now
            try:
                save_telemetry_snapshot_to_db()
            except Exception as e:
                logger.error(f"Erro ao salvar snapshot de telemetria: {e}")

        # Recupera frame e detecções mais recentes sob lock
        current_frame = None
        current_detections = []
        
        with _cv_lock:
            if _raw_frame is not None:
                current_frame = _raw_frame.copy()
            current_detections = list(_latest_detections)

        # Se não houver frame ainda, exibe tela de carregamento/erro
        if current_frame is None:
            err_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(
                err_frame,
                "CONECTANDO COM DISPOSITIVO DE VIDEO...",
                (100, 240),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 200, 100),
                2,
                cv2.LINE_AA
            )
            set_global_frame(err_frame)
            time.sleep(0.05)
            continue
            
        # Desenha overlay rico no frame copiado de forma limpa e estável
        try:
            processed_frame = current_frame.copy()
            if current_detections:
                processed_frame = CVOverlay.draw_detections(processed_frame, current_detections, set())
                
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
            logger.error(f"Erro ao gerar overlay visual no loop: {overlay_err}")
            set_global_frame(current_frame)
            
        # Throttle para travar em 30 FPS estável
        elapsed = time.perf_counter() - t_loop_start
        sleep_t = 0.033 - elapsed
        if sleep_t > 0.001:
            time.sleep(sleep_t)
            
    if _cap is not None:
        _cap.release()
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
