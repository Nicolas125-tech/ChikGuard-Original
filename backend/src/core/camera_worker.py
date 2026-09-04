import logging
import math
import os
import threading
import time

import cv2
import numpy as np

logger = logging.getLogger("chikguard.camera_worker")

camera_running = True
_camera_thread = None

def simulate_telemetry_step():
    """Simula dados de telemetria variando com base no estado dos atuadores."""
    import random

    from src.core.fsm_task import actuator_state
    from src.core.state import sensor_state

    temp = sensor_state.get("temperature_c", 0.0)
    if temp == 0.0:
        temp = 24.8
        sensor_state["humidity_pct"] = 62.0
        sensor_state["ammonia_ppm"] = 5.2
        sensor_state["feed_level_pct"] = 78.0
        sensor_state["water_level_pct"] = 88.0

    if actuator_state.get("aquecedor_on", False):
        temp += 0.15 + random.uniform(-0.03, 0.03)
    elif actuator_state.get("ventilacao_on", False):
        temp -= 0.12 + random.uniform(-0.03, 0.03)
    else:
        temp += (23.0 - temp) * 0.01 + random.uniform(-0.02, 0.02)

    temp = max(12.0, min(38.0, temp))

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
        from src.core.state import sensor_state, species_counts, weight_state
        from src.infrastructure.db.session import SessionLocal

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
                cap_instance.set(cv2.CAP_PROP_POS_FRAMES, 0)
            else:
                consecutive_failures += 1
                if consecutive_failures > 30:
                    logger.warning("Conexão com a câmera real perdida no loop de captura.")
                    cap_instance.release()
                    _cap = cv2.VideoCapture(_camera_index)
                    consecutive_failures = 0
                time.sleep(0.05)
            continue

        consecutive_failures = 0
        resized = cv2.resize(frame, (640, 480))

        with _cv_lock:
            _raw_frame = resized

        time.sleep(0.005)



def _compute_iou(box_a: list, box_b: list) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1 = max(ax1, bx1); iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2); iy2 = min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    return inter / float(area_a + area_b - inter)

def _is_human_shaped(box: list, frame_h: int, frame_w: int) -> bool:
    x1, y1, x2, y2 = box
    w = max(1, x2 - x1); h = max(1, y2 - y1)
    ar = w / h
    area_ratio = (w * h) / max(1, frame_h * frame_w)
    return ar < 0.55 and area_ratio > 0.03

def _sync_batch_age(now_ts, last_batch_query_ts, species_classifier, logger):
    if now_ts - last_batch_query_ts >= 15.0:
        try:
            from datetime import datetime

            from database import Batch
            from src.infrastructure.db.session import SessionLocal
            db_session = SessionLocal()
            active_batch = db_session.query(Batch).filter_by(active=True).first()
            if active_batch:
                age_days = (datetime.utcnow() - active_batch.start_date.replace(tzinfo=None)).days
                age_days = max(1, age_days)
                species_classifier.set_batch_age(age_days)
                logger.info(f"Fator de idade do lote sincronizado: {age_days} dias.")
            else:
                species_classifier.set_batch_age(5)
            db_session.close()
        except Exception as db_err:
            logger.error(f"Erro ao consultar DB para idade do lote: {db_err}")
        return now_ts
    return last_batch_query_ts

def _run_yolo_inference(model, enhanced_detector, frame_to_process, logger):
    frame_h, frame_w = frame_to_process.shape[:2]

    if enhanced_detector:
        raw_enhanced = enhanced_detector.detect(frame_to_process, run_heavy_inference=True)
        results = None
        has_boxes = len(raw_enhanced) > 0

        boxes = np.array([d["box"] for d in raw_enhanced]) if raw_enhanced else np.empty((0, 4))
        confs = np.array([d["confidence"] for d in raw_enhanced]) if raw_enhanced else np.empty((0,))
        clss = np.array([d["class_id"] for d in raw_enhanced]) if raw_enhanced else np.empty((0,))
        ids = np.array([d["track_id"] for d in raw_enhanced]) if raw_enhanced else np.empty((0,))
    else:
        results = model.track(
            frame_to_process,
            persist=True,
            tracker="bytetrack.yaml",
            conf=0.15,
            iou=0.45,
            imgsz=960,
            verbose=False,
            agnostic_nms=True,
        )
        has_boxes = False
        if results and results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confs = results[0].boxes.conf.cpu().numpy()
            clss = results[0].boxes.cls.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy() if results[0].boxes.id is not None else [-1] * len(boxes)
            has_boxes = len(boxes) > 0
        else:
            boxes, confs, clss, ids = [], [], [], []

    tile_results_extra = []
    if not enhanced_detector:
        try:
            tiles = [
                (0,           0,           frame_w//2, frame_h//2),
                (frame_w//2,  0,           frame_w,    frame_h//2),
                (0,           frame_h//2,  frame_w//2, frame_h),
                (frame_w//2,  frame_h//2,  frame_w,    frame_h),
            ]
            for tx1, ty1, tx2, ty2 in tiles:
                tile = frame_to_process[ty1:ty2, tx1:tx2]
                if tile.size == 0:
                    continue
                tile_r = model.predict(tile, conf=0.18, imgsz=640, verbose=False)
                if tile_r and tile_r[0].boxes is not None:
                    tb = tile_r[0].boxes.xyxy.cpu().numpy()
                    tc = tile_r[0].boxes.conf.cpu().numpy()
                    tl = tile_r[0].boxes.cls.cpu().numpy()
                    for j in range(len(tb)):
                        bx1, by1, bx2, by2 = tb[j]
                        tile_results_extra.append({
                            "box": [int(bx1+tx1), int(by1+ty1), int(bx2+tx1), int(by2+ty1)],
                            "conf": float(tc[j]),
                            "cls":  int(tl[j]),
                            "tid":  -1,
                        })
        except Exception as tile_err:
            logger.debug(f"Tiling opcional falhou (ignorado): {tile_err}")

    return has_boxes, boxes, confs, clss, ids, tile_results_extra

def _process_detections(has_boxes, boxes, confs, clss, ids, tile_results_extra, frame_to_process, pose_analyzer, species_classifier):
    new_detections = []
    chicks_count = 0
    hens_count = 0
    person_detected = False
    person_boxes = []

    frame_h, frame_w = frame_to_process.shape[:2]
    BIRD_CANDIDATE_CLASSES = {14, 15, 16, 18, 19, 21}

    if has_boxes:
        for i in range(len(boxes)):
            cid = int(clss[i])
            if cid == 0:
                person_boxes.append([int(v) for v in boxes[i]])

        raw_candidates = []
        for i in range(len(boxes)):
            raw_candidates.append({
                "box": [int(v) for v in boxes[i]],
                "conf": float(confs[i]),
                "cls":  int(clss[i]),
                "tid":  int(ids[i]),
            })
        for te in tile_results_extra:
            te_box = te["box"]
            is_dup = any(_compute_iou(te_box, rc["box"]) > 0.50 for rc in raw_candidates)
            if not is_dup:
                raw_candidates.append(te)

        for cand in raw_candidates:
            box  = cand["box"]
            conf = cand["conf"]
            cid  = cand["cls"]
            uid  = cand["tid"]

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
                    "color": (0, 0, 255),
                    "pose_label": "ATENÇÃO"
                }
                new_detections.append(det)
                continue

            if cid not in BIRD_CANDIDATE_CLASSES:
                continue

            is_overlapping_human = any(_compute_iou(box, pb) > 0.35 for pb in person_boxes)
            if is_overlapping_human:
                continue

            if _is_human_shaped(box, frame_h, frame_w):
                continue

            if cid != 14 and conf < 0.22:
                continue

            pose_info = pose_analyzer.analyze(box, 0.0, frame_to_process.shape)
            species_info = species_classifier.classify(frame_to_process, box, "bird", 0.0, track_id=uid)

            det = {
                "box": box,
                "confidence": conf,
                "class_id": 14,
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

    return new_detections, chicks_count, hens_count, person_detected


def _process_immobile_birds(new_detections, now_ts, immobility_state):
    bird_boxes = []
    bird_centers = []
    carcass_items = []

    for d in new_detections:
        if d.get("class_id") == 14 or d.get("species") in ("chick", "hen", "bird"):
            box = d["box"]
            uid = d.get("track_id", -1)
            bird_boxes.append(box)
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0
            bird_centers.append((cx, cy))

            if uid >= 0:
                if uid not in immobility_state:
                    immobility_state[uid] = {
                        "anchor": (cx, cy),
                        "since": now_ts,
                        "alerted": False
                    }
                else:
                    st = immobility_state[uid]
                    ax, ay = st["anchor"]
                    dist = math.hypot(cx - ax, cy - ay)
                    if dist > 15.0:
                        st["anchor"] = (cx, cy)
                        st["since"] = now_ts
                        st["alerted"] = False
                        d["is_immobile"] = False
                    else:
                        inact_sec = now_ts - float(st["since"])
                        if inact_sec > 300.0:
                            st["alerted"] = True
                            d["is_immobile"] = True
                            carcass_items.append({
                                "bird_uid": int(uid),
                                "x": int(cx),
                                "y": int(cy),
                                "immobile_seconds": round(inact_sec, 1)
                            })
    return bird_boxes, bird_centers, carcass_items

def _process_zone_analytics(bird_centers, frame_w, frame_h, now_ts, tri_zone_analyzer, zone_time_series, zone_analytics_state, cv_lock, logger):
    z_res = None
    if tri_zone_analyzer and bird_centers:
        try:
            z_res = tri_zone_analyzer.analyze_zones(bird_centers, frame_w, frame_h, timestamp=now_ts)
            with cv_lock:
                zone_analytics_state["drinker_count"] = z_res["drinker_count"]
                zone_analytics_state["brooder_count"] = z_res["brooder_count"]
                zone_analytics_state["feeder_count"] = z_res["feeder_count"]
                zone_analytics_state["drinker_pct"] = z_res["drinker_pct"]
                zone_analytics_state["brooder_pct"] = z_res["brooder_pct"]
                zone_analytics_state["feeder_pct"] = z_res["feeder_pct"]
                zone_analytics_state["welfare_status"] = z_res["welfare_status"]
                zone_analytics_state["welfare_message"] = z_res["welfare_message"]
                zone_analytics_state["welfare_index"] = z_res["welfare_index"]
                zone_analytics_state["updated_at"] = now_ts
        except Exception as z_err:
            logger.debug(f"Análise de zonamento trifásico falhou: {z_err}")

    if zone_time_series and z_res:
        try:
            zone_time_series.record_sample(
                drinker_count=z_res["drinker_count"],
                brooder_count=z_res["brooder_count"],
                feeder_count=z_res["feeder_count"],
                timestamp=now_ts
            )
        except Exception as ts_err:
            logger.debug(f"Falha ao registrar série temporal de permanência: {ts_err}")
    return z_res

def _process_additional_plugins(new_detections, bird_centers, frame_to_process, frame_w, frame_h, now_ts, paper_subtractor, spatial_heatmap, weight_estimator, biosafety_plugin, active_camera_id, species_classifier, weight_state, cv_lock, logger):
    if paper_subtractor and frame_to_process is not None:
        try:
            paper_subtractor.process_frame(frame_to_process)
        except Exception as ps_err:
            logger.debug(f"Subtrator clássico de fundo falhou: {ps_err}")

    if spatial_heatmap and bird_centers:
        try:
            spatial_heatmap.add_detections(bird_centers, frame_w, frame_h, timestamp=now_ts)
        except Exception as sh_err:
            logger.debug(f"Falha ao acumular heatmap espacial: {sh_err}")

    if weight_estimator and new_detections:
        try:
            current_age = getattr(species_classifier, "_batch_age_day", 14)
            flock_weight = weight_estimator.estimate_flock_weight(
                new_detections, frame_to_process.shape, batch_age_days=current_age
            )
            with cv_lock:
                weight_state["avg_weight_g"] = flock_weight["avg_weight_g"]
                weight_state["count"] = flock_weight["count"]
                weight_state["confidence"] = flock_weight["confidence"]
                weight_state["updated_at"] = now_ts
        except Exception as w_err:
            logger.debug(f"Falha na estimativa de peso biométrico: {w_err}")

    if biosafety_plugin and active_camera_id in ("ENTRANCE", "SANITARY_BARRIER"):
        try:
            biosafety_plugin.process_frame(frame_to_process, active_camera_id)
        except Exception as bio_err:
            logger.debug(f"Auditoria de biossegurança ignorada: {bio_err}")

def _calculate_dispersion_metrics(bird_boxes, bird_centers, frame_w, frame_h):
    tot_birds = len(bird_boxes)
    edge_count = 0
    disp_ratio = 0.5
    edge_ratio = 0.1
    if tot_birds > 0 and frame_w > 0 and frame_h > 0:
        for b in bird_boxes:
            if b[0] < 0.08 * frame_w or b[2] > 0.92 * frame_w or b[1] < 0.08 * frame_h or b[3] > 0.92 * frame_h:
                edge_count += 1
        edge_ratio = round(edge_count / tot_birds, 2)
        if tot_birds > 1:
            dists = []
            for i in range(min(tot_birds, 20)):
                for j in range(i + 1, min(tot_birds, 20)):
                    d = math.hypot(bird_centers[i][0] - bird_centers[j][0], bird_centers[i][1] - bird_centers[j][1])
                    dists.append(d)
            if dists:
                avg_d = sum(dists) / len(dists)
                diag = math.hypot(frame_w, frame_h)
                disp_ratio = round(avg_d / max(1.0, diag), 2)

    status_str = "NORMAL"
    msg_str = "Dispersão homogênea do lote"
    if edge_ratio > 0.40:
        status_str = "ESTRESSE_TERMICO"
        msg_str = "Atenção: Aves aglomeradas nas bordas (estresse térmico / frio)"
    elif disp_ratio < 0.20:
        status_str = "AMONTOAMENTO"
        msg_str = "Alerta: Alta densidade e amontoamento de aves"

    return status_str, msg_str, disp_ratio, edge_ratio, tot_birds

def _apply_analytics_plugins(new_detections, frame_to_process, now_ts, tri_zone_analyzer, zone_time_series, paper_subtractor, spatial_heatmap, weight_estimator, biosafety_plugin, active_camera_id, species_classifier, logger):
    from src.core.state import cv_lock, immobility_state, weight_state, zone_analytics_state

    frame_h, frame_w = frame_to_process.shape[:2]

    bird_boxes, bird_centers, carcass_items = _process_immobile_birds(
        new_detections, now_ts, immobility_state
    )

    _process_zone_analytics(
        bird_centers, frame_w, frame_h, now_ts,
        tri_zone_analyzer, zone_time_series, zone_analytics_state, cv_lock, logger
    )

    _process_additional_plugins(
        new_detections, bird_centers, frame_to_process, frame_w, frame_h, now_ts,
        paper_subtractor, spatial_heatmap, weight_estimator, biosafety_plugin,
        active_camera_id, species_classifier, weight_state, cv_lock, logger
    )

    status_str, msg_str, disp_ratio, edge_ratio, tot_birds = _calculate_dispersion_metrics(
        bird_boxes, bird_centers, frame_w, frame_h
    )

    return carcass_items, status_str, msg_str, disp_ratio, edge_ratio, tot_birds

def _save_db_metrics(now_ts, last_db_save_ts, logger):
    if now_ts - last_db_save_ts >= 5.0:
        try:
            from database import SensorReading, WeightEstimate
            from src.core.state import sensor_state, species_counts, weight_state
            from src.infrastructure.db.session import SessionLocal

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
        return now_ts
    return last_db_save_ts

def _inference_thread_func(
    model, species_classifier, pose_analyzer, enhanced_detector=None,
    behavior_engine=None, gait_analyzer=None, biosafety_plugin=None,
    tamper_detector=None, spatial_heatmap=None, weight_estimator=None,
    radial_corrector=None, tri_zone_analyzer=None, zone_time_series=None,
    paper_subtractor=None
):
    """Thread dedicada de inferência YOLOv8 - processa frames de forma assíncrona com sincronização local/nuvem."""
    global _raw_frame, _latest_detections, camera_running

    last_batch_query_ts = 0.0
    last_db_save_ts = 0.0
    frame_counter = 0

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

        # 0. Correção Radial de Iluminação da Campânula
        if radial_corrector:
            try:
                frame_to_process = radial_corrector.correct_intensity(frame_to_process)
            except Exception as rc_err:
                logger.debug(f"Correção radial de intensidade falhou: {rc_err}")

        # 1. Análise Anti-Sabotagem e Qualidade da Câmera
        if tamper_detector:
            try:
                t_res = tamper_detector.analyze_frame(frame_to_process)
                from src.core.state import cv_lock, tamper_state
                with cv_lock:
                    if t_res["tamper_detected"]:
                        tamper_state["last_alert_ts"] = now_ts
                        tamper_state["alerts_count"] += 1
                    tamper_state["last_causes"] = t_res["causes"]
                    tamper_state["dark_frames"] = t_res["dark_counter"]
                    tamper_state["freeze_frames"] = t_res["freeze_counter"]
            except Exception as t_err:
                logger.debug(f"Detector de tamper falhou: {t_err}")

        # 2. Consulta idade do lote do DB
        last_batch_query_ts = _sync_batch_age(now_ts, last_batch_query_ts, species_classifier, logger)

        # 3. Inferência YOLO
        try:
            has_boxes, boxes, confs, clss, ids, tile_results_extra = _run_yolo_inference(
                model, enhanced_detector, frame_to_process, logger
            )

            new_detections, chicks_count, hens_count, person_detected = _process_detections(
                has_boxes, boxes, confs, clss, ids, tile_results_extra, frame_to_process, pose_analyzer, species_classifier
            )

            # 4. Plugins e Analytics
            from src.core.state import active_camera_id
            carcass_items, status_str, msg_str, disp_ratio, edge_ratio, tot_birds = _apply_analytics_plugins(
                new_detections, frame_to_process, now_ts, tri_zone_analyzer, zone_time_series, paper_subtractor,
                spatial_heatmap, weight_estimator, biosafety_plugin, active_camera_id, species_classifier, logger
            )

            # Atualizar Estado Global
            from src.core.state import (
                behavior_state,
                carcass_state,
                cv_lock,
                intrusion_state,
                live_birds,
                species_counts,
            )

            with cv_lock:
                intrusion_state["active"] = person_detected
                if person_detected:
                    intrusion_state["last_alert_ts"] = time.time()
                    intrusion_state["alerts_count"] += 1

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

                behavior_state["status"] = status_str
                behavior_state["message"] = msg_str
                behavior_state["dispersion_ratio"] = disp_ratio
                behavior_state["edge_ratio"] = edge_ratio
                behavior_state["count"] = tot_birds
                behavior_state["updated_at"] = now_ts

                carcass_state["count"] = len(carcass_items)
                carcass_state["items"] = carcass_items
                carcass_state["updated_at"] = now_ts

            with _cv_lock:
                _latest_detections = new_detections

            last_db_save_ts = _save_db_metrics(now_ts, last_db_save_ts, logger)

        except Exception as cv_err:
            logger.error(f"Erro no processamento YOLO da thread: {cv_err}")

        time.sleep(0.01)




def _init_camera(camera_index, logger):
    """Initializes the real camera or falls back to simulation video."""
    global _cap, _use_sim

    _cap = None
    _use_sim = False

    import cv2

    try:
        _cap = cv2.VideoCapture(camera_index)
        if _cap.isOpened():
            ret, _ = _cap.read()
            if ret:
                logger.info(f"Câmera real {camera_index} iniciada com sucesso.")
            else:
                _cap.release()
                _cap = None
    except Exception as exc:
        logger.warning(f"Erro ao abrir câmera real: {exc}")
        _cap = None

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

    return _cap, _use_sim

def _instantiate_plugin(plugin_key, settings, model_path, logger):
    """Helper to instantiate a single CV plugin."""
    try:
        if plugin_key == "enhanced_detector":
            import os

            from src.domain.vision.enhanced_detector import EnhancedObjectDetector
            return EnhancedObjectDetector(model_path=model_path if os.path.exists(model_path) else "yolov8n.pt")
        elif plugin_key == "behavior_engine":
            from src.application.cv_master.behavior_engine import BehaviorEngine
            return BehaviorEngine()
        elif plugin_key == "gait_analyzer":
            from src.domain.vision.gait_analyzer import GaitAnalyzer
            return GaitAnalyzer()
        elif plugin_key == "biosafety_plugin":
            from plugins.biosafety_audit.plugin import BiosafetyAuditPlugin
            plugin = BiosafetyAuditPlugin()
            plugin.on_startup({"settings": settings})
            return plugin
        elif plugin_key == "tamper_detector":
            from src.domain.vision.tamper_detector import CameraTamperDetector
            return CameraTamperDetector()
        elif plugin_key == "spatial_heatmap":
            from src.domain.vision.spatial_heatmap import SpatialHeatmapAccumulator
            plugin = SpatialHeatmapAccumulator()
            from src.core import state
            state.spatial_accumulator = plugin
            return plugin
        elif plugin_key == "weight_estimator":
            from src.domain.vision.weight_estimator import BiometricWeightEstimator
            return BiometricWeightEstimator()
        elif plugin_key == "radial_corrector":
            from src.domain.vision.radial_light_corrector import RadialBrooderLightCorrector
            return RadialBrooderLightCorrector()
        elif plugin_key == "tri_zone_analyzer":
            from src.domain.vision.tri_zone_analyzer import TriZoneBehaviorAnalyzer
            return TriZoneBehaviorAnalyzer()
        elif plugin_key == "zone_time_series":
            from src.domain.vision.zone_time_series import ZoneTimeSeriesTracker
            plugin = ZoneTimeSeriesTracker()
            from src.core import state
            state.zone_time_series_tracker = plugin
            return plugin
        elif plugin_key == "paper_subtractor":
            from src.domain.vision.background_subtractor_paper import PaperBackgroundSubtractor
            return PaperBackgroundSubtractor()
    except Exception as exc:
        logger.warning(f"{plugin_key} não inicializado: {exc}")
    return None

def _init_models_and_plugins(settings, logger):
    """Initializes YOLO and all computer vision plugins."""
    from ultralytics import YOLO

    from src.core.cv_engine import BirdPoseAnalyzer, SpeciesClassifier

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
        model_path = "yolov8n.pt"

    plugin_keys = [
        "enhanced_detector", "behavior_engine", "gait_analyzer", "biosafety_plugin",
        "tamper_detector", "spatial_heatmap", "weight_estimator", "radial_corrector",
        "tri_zone_analyzer", "zone_time_series", "paper_subtractor"
    ]

    plugins = {
        key: _instantiate_plugin(key, settings, model_path, logger)
        for key in plugin_keys
    }

    return model, species_classifier, pose_analyzer, plugins

def _run_coordinator_loop(model, plugins, logger):
    """Main coordinator loop for processing frames and overlaying metrics."""
    global camera_running, _raw_frame, _latest_detections, _cv_lock, _cap
    import time

    import cv2

    from src.core.camera_worker import save_telemetry_snapshot_to_db, simulate_telemetry_step
    from src.core.cv_engine import CVOverlay
    from src.core.state import set_global_frame, species_counts

    last_telemetry_sim_ts = 0.0
    last_db_save_ts = 0.0
    print("[CAMERA WORKER] Entering main coordinator loop...")

    enhanced_detector = plugins.get("enhanced_detector")

    while camera_running:
        t_loop_start = time.perf_counter()

        now = time.time()
        if now - last_telemetry_sim_ts >= 1.0:
            last_telemetry_sim_ts = now
            try:
                simulate_telemetry_step()
            except Exception as e:
                logger.error(f"Erro na simulação de telemetria: {e}")

        if now - last_db_save_ts >= 3.0:
            last_db_save_ts = now
            try:
                save_telemetry_snapshot_to_db()
            except Exception as e:
                logger.error(f"Erro ao salvar snapshot de telemetria: {e}")

        current_frame = None
        current_detections = []

        with _cv_lock:
            if _raw_frame is not None:
                current_frame = _raw_frame.copy()
            current_detections = list(_latest_detections)

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

        try:
            processed_frame = current_frame.copy()
            if current_detections:
                try:
                    from src.security.privacy import anonymize_human_detections
                    processed_frame = anonymize_human_detections(processed_frame, current_detections)
                except Exception as priv_err:
                    logger.debug(f"Anonimização LGPD ignorada: {priv_err}")
                processed_frame = CVOverlay.draw_detections(processed_frame, current_detections, set())

            backend_name = "pytorch"
            sahi_enabled = False
            if enhanced_detector:
                backend_name = enhanced_detector.backend_name
                sahi_enabled = enhanced_detector.sahi_enabled

            metrics_dict = {
                "fps_camera": 30.0,
                "fps_inference": 10.0 if (model or enhanced_detector) else 0.0,
                "latency_ms": 45.0 if (model or enhanced_detector) else 0.0,
                "sahi_enabled": sahi_enabled,
                "backend_name": backend_name
            }

            from src.core.state import behavior_state, zone_analytics_state
            status_text = f"Bem-Estar: {zone_analytics_state.get('welfare_status', behavior_state.get('status', 'NORMAL'))}"

            processed_frame = CVOverlay.draw_hud(
                processed_frame,
                metrics_dict,
                species_counts,
                status_text
            )

            set_global_frame(processed_frame)
        except Exception as overlay_err:
            logger.error(f"Erro ao gerar overlay visual no loop: {overlay_err}")
            set_global_frame(current_frame)

        elapsed = time.perf_counter() - t_loop_start
        sleep_t = 0.033 - elapsed
        if sleep_t > 0.001:
            time.sleep(sleep_t)

    if _cap is not None:
        _cap.release()
    logger.info("camera_worker encerrado.")

def camera_worker():
    """Main function for the camera worker process."""
    global camera_running, _camera_index
    import threading

    from src.core.camera_worker import _capture_thread_func, _inference_thread_func, logger
    from src.core.config import load_settings

    settings = load_settings()
    _camera_index = settings.camera_index

    logger.info(f"Iniciando camera_worker. Câmera Index: {_camera_index}")
    print(f"[CAMERA WORKER] Starting... camera_index={_camera_index}")

    _init_camera(_camera_index, logger)

    model, species_classifier, pose_analyzer, plugins = _init_models_and_plugins(settings, logger)

    capture_thread = threading.Thread(target=_capture_thread_func, name="CaptureThread", daemon=True)
    capture_thread.start()

    inference_thread = None
    if model is not None or plugins.get("enhanced_detector") is not None:
        inference_thread = threading.Thread(
            target=_inference_thread_func,
            args=(
                model, species_classifier, pose_analyzer, plugins.get("enhanced_detector"),
                plugins.get("behavior_engine"), plugins.get("gait_analyzer"), plugins.get("biosafety_plugin"),
                plugins.get("tamper_detector"), plugins.get("spatial_heatmap"), plugins.get("weight_estimator"),
                plugins.get("radial_corrector"), plugins.get("tri_zone_analyzer"), plugins.get("zone_time_series"),
                plugins.get("paper_subtractor")
            ),
            name="InferenceThread",
            daemon=True
        )
        inference_thread.start()

    _run_coordinator_loop(model, plugins, logger)

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
