import os
import time
import math
import logging
import threading
import json
import asyncio
from datetime import datetime
from typing import Optional
import cv2
import numpy as np

import src.core.state as state
from src.core.state import cv_lock
from src.cv_master.inference_sota import SOTAInferenceEngine
from src.cv_master.tracker_spy import SpyTracker
from src.cv_master.behavior_engine import BehaviorEngine
from src.core.cv_engine import SpeciesClassifier, BirdPoseAnalyzer, PerfMetrics
from src.vision.gait_analyzer import GaitAnalyzer
from src.api.fastapi_ws import emit_new_alert
from src.db.session import SessionLocal
from database import Reading, BirdSnapshot, BirdTrackPoint, EventLog, SyncQueueItem, Batch


def _estimate_keypoints_from_box(box, tid, now_ts):
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    w = max(1.0, x2 - x1)
    h = max(1.0, y2 - y1)
    
    # Simula oscilação de passos no tempo para o track_id correspondente
    offset = 5.0 * math.sin(now_ts * 12.0)
    left_foot_y = y2 + (offset if tid % 2 == 0 else -offset)
    right_foot_y = y2 + (-offset if tid % 2 == 0 else offset)
    
    # Retorna 11 keypoints [[x, y, conf], ...] no formato YOLOv8-pose
    return [
        [cx, cy - h*0.2, 0.9],          # Beak
        [cx - w*0.1, cy - h*0.22, 0.8], # Eye L
        [cx + w*0.1, cy - h*0.22, 0.8], # Eye R
        [cx, cy - h*0.1, 0.9],          # Neck
        [cx - w*0.3, cy - h*0.05, 0.7], # Wing L
        [cx + w*0.3, cy - h*0.05, 0.7], # Wing R
        [cx, cy, 0.9],                  # Hip
        [cx - w*0.15, cy + h*0.2, 0.9],  # Knee L
        [cx + w*0.15, cy + h*0.2, 0.9],  # Knee R
        [cx - w*0.2, left_foot_y, 0.9],  # Foot L
        [cx + w*0.2, right_foot_y, 0.9], # Foot R
    ]


class SOTAPipelineRunner:
    def __init__(self):
        self.logger = logging.getLogger("cv_runner.SOTAPipelineRunner")
        self.running = False
        self.thread = None
        self.loop = None
        
        # Load configs from ENV
        self.video_src = os.getenv("SIM_VIDEO_PATH", "video_granja.mp4")
        self.model_path = os.getenv("YOLO_SEG_MODEL_PATH", "yolov8n-seg.pt")
        
        # Resolve target video source (int index vs filepath)
        try:
            self.video_src = int(self.video_src)
        except ValueError:
            pass

        self.logger.info(f"SOTA Pipeline Runner inicializado: src={self.video_src}, model={self.model_path}")
        
        # Configurações de Tamper/Violacão (skill guide)
        self.TAMPER_DARK_MEAN_THRESHOLD = float(os.getenv("TAMPER_DARK_MEAN_THRESHOLD", "24.0"))
        self.TAMPER_LOW_TEXTURE_STD_THRESHOLD = float(os.getenv("TAMPER_LOW_TEXTURE_STD_THRESHOLD", "8.0"))
        self.TAMPER_FREEZE_DIFF_THRESHOLD = float(os.getenv("TAMPER_FREEZE_DIFF_THRESHOLD", "1.2"))
        self.TAMPER_FREEZE_MIN_FRAMES = int(os.getenv("TAMPER_FREEZE_MIN_FRAMES", "45"))
        self.TAMPER_SENSOR_STALE_SEC = int(os.getenv("TAMPER_SENSOR_STALE_SEC", "180"))
        self.TAMPER_ALERT_COOLDOWN_SEC = int(os.getenv("TAMPER_ALERT_COOLDOWN_SEC", "180"))
        self.TAMPER_BLUR_LAPLACIAN_THRESHOLD = 10.0 # Lap_var < 10 indica desfocado ou poeira excessiva
        
        # Buffers temporais para tamper
        self.prev_gray = None
        self.last_visible_frame = None
        
        # Engines
        self.inference = None
        self.tracker = None
        self.behavior = None
        self.gait_analyzer = None
        self.species_classifier = None
        self.pose_analyzer = None
        self.perf_metrics = None
        
        self.last_annotated = np.zeros((480, 640, 3), dtype=np.uint8)
        self.last_tracked = None

    def start(self, loop=None):
        if self.running:
            return
        self.running = True
        self.loop = loop or asyncio.get_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="sota-cv-runner")
        self.thread.start()
        self.logger.info("SOTA CV Runner iniciado em thread paralela.")

    def _evaluate_tamper_conditions(self, frame, now):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_luma = float(np.mean(gray))
        std_luma = float(np.std(gray))
        
        # 1. Checagem de Obstrução/Escuridão
        visible_ok = (
            mean_luma >= self.TAMPER_DARK_MEAN_THRESHOLD
            and std_luma >= self.TAMPER_LOW_TEXTURE_STD_THRESHOLD
        )
        if visible_ok:
            state.tamper_state["dark_frames"] = 0
            self.last_visible_frame = frame.copy()
        else:
            state.tamper_state["dark_frames"] = int(state.tamper_state.get("dark_frames", 0)) + 1

        # 2. Checagem de Congelamento de Frame
        if self.prev_gray is None or self.prev_gray.shape != gray.shape:
            self.prev_gray = gray.copy()
            diff = 100.0
        else:
            diff = float(np.mean(cv2.absdiff(gray, self.prev_gray)))
            self.prev_gray = gray.copy()
            if diff < self.TAMPER_FREEZE_DIFF_THRESHOLD:
                state.tamper_state["freeze_frames"] = int(state.tamper_state.get("freeze_frames", 0)) + 1
            else:
                state.tamper_state["freeze_frames"] = 0

        # 3. Checagem de Lente Desfocada/Empoeirada (Variância do Laplaciano)
        if visible_ok:
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            state.tamper_state["lens_dirty"] = lap_var < self.TAMPER_BLUR_LAPLACIAN_THRESHOLD
        else:
            state.tamper_state["lens_dirty"] = False

        # 4. Checagem de Sensores Stale
        sensor_updated_at = float(state.sensor_state.get("updated_at", 0.0))
        sensor_stale = (now - sensor_updated_at) > self.TAMPER_SENSOR_STALE_SEC
        state.tamper_state["sensor_stale"] = bool(sensor_stale)

    def _get_active_tamper_causes(self) -> list:
        causes = []
        if int(state.tamper_state.get("dark_frames", 0)) >= 8:
            causes.append("camera_obstruida")
        if int(state.tamper_state.get("freeze_frames", 0)) >= self.TAMPER_FREEZE_MIN_FRAMES:
            causes.append("camera_congelada")
        if state.tamper_state.get("lens_dirty", False):
            causes.append("lente_suja_ou_desfocada")
        if state.tamper_state.get("sensor_stale", False):
            causes.append("sensor_sem_update")
        return causes

    def _emit_tamper_alerts(self, causes: list, now: float):
        last_alert_ts = float(state.tamper_state.get("last_alert_ts", 0.0))
        if now - last_alert_ts < self.TAMPER_ALERT_COOLDOWN_SEC:
            return

        state.tamper_state["last_alert_ts"] = now
        state.tamper_state["alerts_count"] = int(state.tamper_state.get("alerts_count", 0)) + 1

        msg_map = {
            "camera_obstruida": "Câmera obstruída ou sem luz.",
            "camera_congelada": "Câmera travada/congelada.",
            "lente_suja_ou_desfocada": "Lente embaçada ou com excesso de poeira.",
            "sensor_sem_update": "Telemetria de sensores offline."
        }
        alert_messages = [msg_map[c] for c in causes if c in msg_map]
        combined_msg = " | ".join(alert_messages)

        try:
            db = SessionLocal()
            log_entry = EventLog(
                camera_id="galpao-1",
                event_type="camera_tampering",
                level="warning",
                message=f"Tamper detectado: {combined_msg}",
                metadata_json=json.dumps({"causes": causes}),
                timestamp=datetime.utcnow()
            )
            db.add(log_entry)
            db.flush()
            
            db.add(SyncQueueItem(
                item_type="event_log",
                payload_json=json.dumps(log_entry.to_dict()),
                status="pending"
            ))
            db.commit()
            db.close()
        except Exception as db_err:
            self.logger.error(f"Erro ao salvar alerta de tamper no DB: {db_err}")

        if self.loop is not None:
            asyncio.run_coroutine_threadsafe(
                emit_new_alert({
                    "type": "camera_tampering",
                    "level": "warning",
                    "message": f"Tamper detectado: {combined_msg}",
                    "timestamp": now
                }),
                self.loop
            )

    def _check_camera_tampering(self, frame, now) -> list:
        """
        Detecta obstrução, congelamento, desfocagem/sujeira na lente e telemetria de sensores inativa.
        Atualiza o estado global e retorna a lista de causas ativas.
        """
        if frame is None or frame.size == 0:
            return []

        self._evaluate_tamper_conditions(frame, now)
        causes = self._get_active_tamper_causes()
        state.tamper_state["last_causes"] = list(causes)

        if causes:
            self._emit_tamper_alerts(causes, now)

        return causes

    def _run_loop(self):
        self.logger.info("Carregando modelos AI e inicializando motores...")
        try:
            self.inference = SOTAInferenceEngine(model_path=self.model_path)
            self.tracker = SpyTracker(track_activation_threshold=0.30, lost_track_buffer=90)
            self.behavior = BehaviorEngine(immobility_threshold=10.0, immobility_time_sec=120)
            self.gait_analyzer = GaitAnalyzer(history_len=20)
            self.species_classifier = SpeciesClassifier()
            self.pose_analyzer = BirdPoseAnalyzer()
            self.perf_metrics = PerfMetrics()
            self.perf_metrics.set_backend(self.inference.device)
        except Exception as e:
            self.logger.exception(f"Erro fatal na carga do pipeline de CV: {e}")
            self.running = False
            return

        # Background subtractor for Motion Detection Skipping (skill guidelines)
        bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=100, varThreshold=25, detectShadows=False
        )

        cap = None
        last_db_save = 0.0
        last_batch_sync = 0.0
        last_snapshot_save = 0.0
        
        # Redirect state frame source
        state.get_global_frame = self.get_annotated_frame
        
        self.logger.info("Fase de warm-up finalizada. Iniciando loop de aquisição.")

        while self.running:
            if cap is None or not cap.isOpened():
                if cap is not None:
                    cap.release()
                self.logger.info(f"Abrindo fonte de captura: {self.video_src}")
                cap = cv2.VideoCapture(self.video_src)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # LIFO buffer logic
                if not cap.isOpened():
                    self.logger.error("Falha ao abrir stream de captura. Re-tentando em 5 segundos.")
                    time.sleep(5.0)
                    continue

            start_time = time.perf_counter()
            ret, frame = cap.read()
            if not ret or frame is None:
                # Se for vídeo de simulação, realiza o loop contínuo
                if isinstance(self.video_src, str) and self.video_src.endswith(".mp4"):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    self.logger.warning("Fim do vídeo ou sinal da câmera perdido. Re-abrindo em 3s.")
                    time.sleep(3.0)
                    cap.release()
                    cap = None
                    continue

            self.perf_metrics.tick_capture()

            now = time.time()

            # Roda checagem de violação/tamper da câmera
            tamper_causes = self._check_camera_tampering(frame, now)

            # 1. CLAHE Contrast Enhancement para condições de baixa iluminação/poeira (skill guide)
            try:
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                l_clahe = clahe.apply(l)
                lab_clahe = cv2.merge((l_clahe, a, b))
                clean_frame = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
            except Exception:
                clean_frame = frame.copy()

            # 2. Heurística de Movimentação (Background Subtractor)
            fg_mask = bg_subtractor.apply(clean_frame)
            motion_pixels = cv2.countNonZero(fg_mask)
            total_pixels = clean_frame.shape[0] * clean_frame.shape[1]
            motion_ratio = float(motion_pixels) / float(total_pixels)

            # Sincroniza idade do lote avícola a cada 30 segundos
            if now - last_batch_sync > 30.0:
                last_batch_sync = now
                try:
                    db = SessionLocal()
                    batch = db.query(Batch).filter_by(camera_id="galpao-1", active=True).order_by(Batch.id.desc()).first()
                    if batch:
                        age = max(1, (datetime.utcnow().date() - batch.start_date.date()).days + 1)
                        self.species_classifier.set_batch_age(age)
                    db.close()
                except Exception:
                    pass

            # 3. Sliced Inference SAHI e Rastreamento ByteTrack
            run_inference = (motion_ratio >= 0.005) or (int(now * 10) % 6 == 0)
            
            try:
                if run_inference:
                    detections = self.inference.process_frame(clean_frame, slice_size=640)
                    tracked = self.tracker.update(detections)
                    self.last_tracked = tracked
                else:
                    tracked = self.last_tracked
            except Exception as cv_err:
                self.logger.error(f"Erro na inferência/rastreamento: {cv_err}")
                tracked = self.last_tracked

            # Conforto térmico por proximidade (Huddling Index)
            huddling_label = "CONFORTO TÉRMICO"
            if tracked is not None and len(tracked) > 1:
                _, huddling_label = self.behavior.calculate_clustering_index(tracked)

            # Enriquecimento zootécnico individual de cada ave
            enriched_detections = []
            now_dt = datetime.utcnow()
            chicks_count = 0
            hens_count = 0

            if tracked is not None and len(tracked) > 0 and tracked.tracker_id is not None:
                for i in range(len(tracked)):
                    tid = int(tracked.tracker_id[i])
                    box = tracked.xyxy[i].tolist()
                    conf = float(tracked.confidence[i])
                    cid = int(tracked.class_id[i])

                    kps = _estimate_keypoints_from_box(box, tid, now)
                    gait_res = self.gait_analyzer.update_track(tid, kps, now_dt)

                    pose_info = self.pose_analyzer.analyze(box, 0.0, clean_frame.shape)
                    species_info = self.species_classifier.classify(clean_frame, box, "bird", 0.0)

                    if species_info["species"] == "chick":
                        chicks_count += 1
                    else:
                        hens_count += 1

                    is_carcass = tid in self.behavior.dead_or_sick_ids

                    enriched_detections.append({
                        "box": [int(v) for v in box],
                        "conf": conf,
                        "track_id": tid,
                        "species": species_info["species"],
                        "species_label": species_info["species_label"],
                        "color": species_info["color"],
                        "pose": pose_info["pose"],
                        "pose_label": pose_info["pose_label"],
                        "is_carcass": is_carcass,
                        "gait": gait_res,
                        "last_seen": now,
                    })

            # 4. Atualização de Estados Globais sob Thread Lock
            with cv_lock:
                for det in enriched_detections:
                    tid = det["track_id"]
                    state.live_birds[tid] = det

                stale_uids = [
                    uid for uid, info in state.live_birds.items()
                    if (now - info["last_seen"]) > 5.0
                ]
                for uid in stale_uids:
                    state.live_birds.pop(uid, None)
                    self.gait_analyzer.remove_track(uid)

                state.species_counts = {
                    "total": len(state.live_birds),
                    "chicks": sum(1 for b in state.live_birds.values() if b["species"] == "chick"),
                    "hens": sum(1 for b in state.live_birds.values() if b["species"] == "hen"),
                    "huddling_status": huddling_label
                }

                if state.live_birds:
                    VIRTUAL_SCALE_CM_PER_PX_AT_1M = 0.09
                    CAMERA_DISTANCE_M = 2.2
                    WEIGHT_CALIBRATION_G_PER_SQRT_PX = 1.85
                    
                    scale = VIRTUAL_SCALE_CM_PER_PX_AT_1M * max(0.5, CAMERA_DISTANCE_M)
                    weights = []
                    for b in state.live_birds.values():
                        x1, y1, x2, y2 = b["box"]
                        area_px = max(1.0, float((x2 - x1) * (y2 - y1)))
                        body_area_cm2 = area_px * (scale ** 2)
                        base_weight = WEIGHT_CALIBRATION_G_PER_SQRT_PX * math.sqrt(body_area_cm2 * 100.0)
                        
                        cy = (y1 + y2) / 2.0
                        perspective = 0.92 + (0.16 * (cy / float(clean_frame.shape[0])))
                        weights.append(base_weight * perspective)

                    avg_weight = float(sum(weights) / len(weights)) if weights else 0.0
                    state.weight_state = {
                        "avg_weight_g": round(avg_weight, 1),
                        "ideal_weight_g": 350.0,
                        "count": len(state.live_birds),
                        "confidence": 0.85,
                        "updated_at": now
                    }

            # 5. Processamento de Alertas de Imobilidade (Carcass)
            if tracked is not None:
                alerts = self.behavior.update_immobility_and_get_alerts(tracked)
                for alert in alerts:
                    try:
                        db = SessionLocal()
                        log_entry = EventLog(
                            camera_id="galpao-1",
                            event_type="carcass_alert",
                            level="high",
                            message=alert["message"],
                            metadata_json=json.dumps({
                                "track_id": alert["track_id"], 
                                "seconds_still": round(alert["seconds_still"], 1)
                            }),
                            timestamp=datetime.utcnow()
                        )
                        db.add(log_entry)
                        db.flush()
                        
                        db.add(SyncQueueItem(
                            item_type="event_log",
                            payload_json=json.dumps(log_entry.to_dict()),
                            status="pending"
                        ))
                        db.commit()
                        db.close()
                    except Exception as db_err:
                        self.logger.error(f"Erro ao salvar alerta de óbito no DB: {db_err}")

                    if self.loop is not None:
                        asyncio.run_coroutine_threadsafe(
                            emit_new_alert({
                                "type": "carcass_alert",
                                "level": "high",
                                "message": alert["message"],
                                "timestamp": now
                            }),
                            self.loop
                        )

            # 6. Renderização Gráfica Premium com Tags de Postura e Espécie
            annotated = clean_frame.copy()
            for det in enriched_detections:
                x1, y1, x2, y2 = det["box"]
                color = det["color"]
                uid = det["track_id"]
                pose_lbl = det["pose_label"]
                gait_lbl = det["gait"]["mobility_status"] if det["gait"].get("status") == "ANALYZED" else "NORMAL"
                
                if det["is_carcass"]:
                    color = (0, 0, 180)

                cv2.rectangle(annotated, (x1 - 1, y1 - 1), (x2 + 1, y2 + 1), (0, 0, 0), 2)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
                
                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                cv2.line(annotated, (cx - 5, cy), (cx + 5, cy), color, 1, cv2.LINE_AA)
                cv2.line(annotated, (cx, cy - 5), (cx, cy + 5), color, 1, cv2.LINE_AA)
                
                cr = 8
                tk = 2
                cv2.line(annotated, (x1, y1), (x1 + cr, y1), color, tk, cv2.LINE_AA)
                cv2.line(annotated, (x1, y1), (x1, y1 + cr), color, tk, cv2.LINE_AA)
                cv2.line(annotated, (x2, y1), (x2 - cr, y1), color, tk, cv2.LINE_AA)
                cv2.line(annotated, (x2, y1), (x2, y1 + cr), color, tk, cv2.LINE_AA)
                cv2.line(annotated, (x1, y2), (x1 + cr, y2), color, tk, cv2.LINE_AA)
                cv2.line(annotated, (x1, y2), (x1, y2 - cr), color, tk, cv2.LINE_AA)
                cv2.line(annotated, (x2, y2), (x2 - cr, y2), color, tk, cv2.LINE_AA)
                cv2.line(annotated, (x2, y2), (x2, y2 - cr), color, tk, cv2.LINE_AA)
                
                id_str = f"#{uid}"
                (tw, th), _ = cv2.getTextSize(id_str, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
                cv2.rectangle(annotated, (x1 - 1, y1 - th - 4), (x1 + tw + 2, y1), (0, 0, 0), -1)
                cv2.putText(annotated, id_str, (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.40, color, 1, cv2.LINE_AA)
                
                sp_tag = f"{det['species_label']} {det['conf']:.0%}"
                cv2.putText(annotated, sp_tag, (x1, y2 + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)
                
                if "NORMAL" not in pose_lbl:
                    cv2.putText(annotated, pose_lbl, (x1, y2 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 80, 255), 1, cv2.LINE_AA)
                elif "NORMAL" not in gait_lbl:
                    cv2.putText(annotated, f"⚠ CLAUDICANDO", (x1, y2 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 180, 255), 1, cv2.LINE_AA)

            # Polígono translúcido de monitoramento
            h, w = annotated.shape[:2]
            mx = int(w * 0.04)
            my = int(h * 0.08)
            zone_pts = np.array([[mx, my], [w - mx, my], [w - mx, h - my], [mx, h - my]], dtype=np.int32)
            
            overlay_poly = annotated.copy()
            cv2.fillPoly(overlay_poly, [zone_pts], (180, 0, 180))
            cv2.addWeighted(overlay_poly, 0.06, annotated, 0.94, 0, annotated)
            cv2.polylines(annotated, [zone_pts], isClosed=True, color=(255, 0, 255), thickness=2, lineType=cv2.LINE_AA)
            cv2.putText(annotated, "ZONA DE MONITORAMENTO", (mx + 6, my - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 0, 255), 1, cv2.LINE_AA)
            
            # Painel HUD Lateral (Topo-direito)
            pw = 260
            ph = 130
            px1 = w - pw - 8
            py1 = 8
            px2 = w - 8
            py2 = py1 + ph
            
            panel = annotated.copy()
            cv2.rectangle(panel, (px1, py1), (px2, py2), (10, 10, 10), -1)
            cv2.addWeighted(panel, 0.75, annotated, 0.25, 0, annotated)
            cv2.rectangle(annotated, (px1, py1), (px2, py2), (0, 255, 100), 1, cv2.LINE_AA)
            
            cv2.putText(annotated, "CHIKGUARD SOTA ENGINE", (px1 + 8, py1 + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 120), 1, cv2.LINE_AA)
            cv2.line(annotated, (px1 + 8, py1 + 21), (px2 - 8, py1 + 21), (0, 255, 100), 1)
            
            total_txt = f"TOTAL AVES: {len(state.live_birds)}"
            cv2.putText(annotated, total_txt, (px1 + 8, py1 + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 60), 2, cv2.LINE_AA)
            
            cv2.putText(annotated, f"PINTINHOS: {chicks_count}", (px1 + 8, py1 + 72), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 220, 255), 1, cv2.LINE_AA)
            cv2.putText(annotated, f"GALINHAS : {hens_count}", (px1 + 8, py1 + 88), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 200, 100), 1, cv2.LINE_AA)
            
            comfort_color = (0, 255, 0) if "CONFORTO" in huddling_label else (0, 140, 255)
            cv2.putText(annotated, f"CONFORTO : {huddling_label}", (px1 + 8, py1 + 106), cv2.FONT_HERSHEY_SIMPLEX, 0.40, comfort_color, 1, cv2.LINE_AA)
            
            if self.behavior.dead_or_sick_ids:
                cv2.putText(annotated, f"ÓBITOS   : {len(self.behavior.dead_or_sick_ids)} DETECTADOS", (px1 + 8, py1 + 122), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 255), 1, cv2.LINE_AA)
            
            # HUD overlay para violação/tamper
            if tamper_causes:
                # Desenha aviso intermitente na parte superior esquerda do HUD
                if int(now * 2.5) % 2 == 0:
                    cv2.rectangle(annotated, (8, 30), (280, 52), (0, 0, 180), -1)
                    cv2.putText(annotated, "⚠ FALHA DE CONEXÃO/TAMPER", (14, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)
            
            # Rodapé informativo
            bar_bg = annotated.copy()
            cv2.rectangle(bar_bg, (0, h - 22), (w, h), (0, 0, 0), -1)
            cv2.addWeighted(bar_bg, 0.60, annotated, 0.40, 0, annotated)
            
            fps_inf = 1.0 / max(1e-6, time.perf_counter() - start_time)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.perf_metrics.tick_inference(latency_ms)
            
            stats_str = f"FPS: {fps_inf:.1f} | Latência: {latency_ms:.1f}ms | Hardware: {self.inference.device.upper()}"
            cv2.putText(annotated, stats_str, (8, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 160, 255), 1, cv2.LINE_AA)
            
            # Ponto LIVE piscante
            if int(now * 2) % 2 == 0:
                cv2.circle(annotated, (12, 14), 5, (0, 0, 255), -1, cv2.LINE_AA)
                cv2.putText(annotated, "LIVE", (22, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 0, 255), 1, cv2.LINE_AA)
            else:
                cv2.circle(annotated, (12, 14), 5, (40, 40, 80), -1, cv2.LINE_AA)
                cv2.putText(annotated, "LIVE", (22, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (80, 80, 120), 1, cv2.LINE_AA)

            # Armazena o frame final no estado global e LIFO buffer
            self.last_annotated = annotated

            # 7. Salva snapshots e trackpoints no banco de dados local a cada 10s
            if now - last_snapshot_save > 10.0:
                last_snapshot_save = now
                try:
                    db = SessionLocal()
                    for det in enriched_detections:
                        tid = det["track_id"]
                        box = det["box"]
                        conf = det["conf"]
                        
                        snapshot = BirdSnapshot(
                            bird_uid=tid,
                            confidence=conf,
                            x1=box[0],
                            y1=box[1],
                            x2=box[2],
                            y2=box[3],
                            temperatura_estimada=25.0,
                            metodo_temperatura="estimada_rgb_proxy",
                            timestamp=datetime.utcnow()
                        )
                        db.add(snapshot)
                        db.flush()
                        
                        db.add(SyncQueueItem(
                            item_type="bird_snapshot",
                            payload_json=json.dumps(snapshot.to_dict()),
                            status="pending"
                        ))

                        cx = int((box[0] + box[2]) / 2)
                        cy = int((box[1] + box[3]) / 2)
                        tp = BirdTrackPoint(
                            bird_uid=tid,
                            x=cx,
                            y=cy,
                            timestamp=datetime.utcnow()
                        )
                        db.add(tp)
                        
                    db.commit()
                    db.close()
                except Exception as db_err:
                    self.logger.error(f"Erro ao salvar snapshots de aves no DB: {db_err}")

            # 8. Salva leituras térmicas estimadas no DB a cada 30 segundos
            if now - last_db_save > 30.0:
                last_db_save = now
                try:
                    db = SessionLocal()
                    gray = cv2.cvtColor(clean_frame, cv2.COLOR_BGR2GRAY)
                    temp_c = 20.0 + (float(np.mean(gray)) / 255.0) * 20.0
                    
                    status = "NORMAL"
                    if temp_c < 24.0:
                        status = "FRIO"
                    elif temp_c > 32.0:
                        status = "CALOR"
                        
                    reading = Reading(
                        temperatura=round(temp_c, 1),
                        status=status,
                        timestamp=datetime.utcnow()
                    )
                    db.add(reading)
                    db.flush()
                    
                    db.add(SyncQueueItem(
                        item_type="reading",
                        payload_json=json.dumps(reading.to_dict()),
                        status="pending"
                    ))
                    db.commit()
                    db.close()
                except Exception as db_err:
                    self.logger.error(f"Erro ao salvar leitura termica no DB: {db_err}")

            # Limitação de processamento a 30 FPS para evitar sobrecarga
            elapsed = time.perf_counter() - start_time
            sleep_t = (1.0 / 30.0) - elapsed
            if sleep_t > 0.001:
                time.sleep(sleep_t)

        if cap is not None:
            cap.release()
        state.get_global_frame = state._default_get_global_frame
        self.logger.info("Thread do SOTA Pipeline Runner finalizada com sucesso.")

    def get_annotated_frame(self):
        return getattr(self, "last_annotated", None)

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        self.logger.info("SOTA Pipeline Runner parado.")


# Instância global unificada
_runner_instance: Optional[SOTAPipelineRunner] = None


def get_sota_runner() -> SOTAPipelineRunner:
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = SOTAPipelineRunner()
    return _runner_instance
