import os
import uuid
import tempfile
import logging
import numpy as np
import cv2

try:
    import requests
except Exception:
    requests = None

from ultralytics import YOLO

# Parametros padrao (os mesmos do app.py, injetados pelas vars de ambiente)
DETECTION_CONF = float(os.getenv("DETECTION_CONF", "0.20"))
DETECTION_IOU = float(os.getenv("DETECTION_IOU", "0.35"))
INFERENCE_IMGSZ = int(os.getenv("INFERENCE_IMGSZ", "640"))
TRACKER_TYPE = os.getenv("TRACKER_TYPE", "bytetrack").strip().lower()
TRACKER_CONFIG = "botsort.yaml" if TRACKER_TYPE == "botsort" else "bytetrack.yaml"
ENABLE_SAHI = os.getenv("ENABLE_SAHI", "False").strip().lower() in ("true", "1", "yes")

LOGGER = logging.getLogger("chikguard.cv.enhanced_detector")

# Simple IoU Tracker fallback if SAHI breaks native tracking
class SimpleIoUTracker:
    def __init__(self, max_lost=15, iou_threshold=0.3):
        self.next_id = 1
        self.tracks = {}
        self.max_lost = max_lost
        self.iou_threshold = iou_threshold

    def update(self, boxes):
        # boxes is list of [x1, y1, x2, y2]
        if len(boxes) == 0:
            for tid in list(self.tracks.keys()):
                self.tracks[tid]['lost'] += 1
                if self.tracks[tid]['lost'] > self.max_lost:
                    del self.tracks[tid]
            return []

        if len(self.tracks) == 0:
            track_ids = []
            for b in boxes:
                self.tracks[self.next_id] = {'box': b, 'lost': 0}
                track_ids.append(self.next_id)
                self.next_id += 1
            return track_ids

        # Compute IoU matrix
        track_ids_list = list(self.tracks.keys())
        track_boxes = [self.tracks[tid]['box'] for tid in track_ids_list]
        num_dets = len(boxes)
        num_tracks = len(track_boxes)
        
        ious = np.zeros((num_dets, num_tracks))
        for i, det in enumerate(boxes):
            dx1, dy1, dx2, dy2 = det
            d_area = (dx2 - dx1) * (dy2 - dy1)
            for j, trk in enumerate(track_boxes):
                tx1, ty1, tx2, ty2 = trk
                t_area = (tx2 - tx1) * (ty2 - ty1)
                
                xx1 = max(dx1, tx1)
                yy1 = max(dy1, ty1)
                xx2 = min(dx2, tx2)
                yy2 = min(dy2, ty2)
                
                w = max(0, xx2 - xx1)
                h = max(0, yy2 - yy1)
                inter = w * h
                iou = inter / float(d_area + t_area - inter + 1e-6)
                ious[i, j] = iou

        assigned_track_ids = [-1] * num_dets
        unassigned_dets = list(range(num_dets))
        unassigned_tracks = list(range(num_tracks))

        while len(unassigned_dets) > 0 and len(unassigned_tracks) > 0:
            max_iou = np.max(ious)
            if max_iou < self.iou_threshold:
                break
            # Find best match
            d_idx, t_idx = np.unravel_index(np.argmax(ious), ious.shape)
            assigned_track_ids[d_idx] = track_ids_list[t_idx]
            self.tracks[track_ids_list[t_idx]]['box'] = boxes[d_idx]
            self.tracks[track_ids_list[t_idx]]['lost'] = 0
            
            unassigned_dets.remove(d_idx)
            unassigned_tracks.remove(t_idx)
            ious[d_idx, :] = -1
            ious[:, t_idx] = -1

        for t_idx in unassigned_tracks:
            tid = track_ids_list[t_idx]
            self.tracks[tid]['lost'] += 1
            if self.tracks[tid]['lost'] > self.max_lost:
                del self.tracks[tid]

        for d_idx in unassigned_dets:
            self.tracks[self.next_id] = {'box': boxes[d_idx], 'lost': 0}
            assigned_track_ids[d_idx] = self.next_id
            self.next_id += 1

        return assigned_track_ids

class EnhancedObjectDetector:
    def __init__(self, model_path="yolov8n.pt"):
        self.yolo_loaded = False
        self.model = None
        self.supports_segmentation = False
        self.encrypted_model_buffer = None
        self.sahi_model = None
        self.tracker = SimpleIoUTracker(max_lost=10, iou_threshold=0.2)
        
        final_model_path = model_path
        
        if model_path.endswith(".enc"):
            try:
                hardware_serial = str(uuid.getnode())
                key = b'chikguard_secure_key'
                if requests is not None:
                    try:
                        resp = requests.post(
                            "http://localhost:5000/api/hardware/unlock",
                            json={"serial": hardware_serial},
                            timeout=5
                        )
                        if resp.ok:
                            data = resp.json()
                            if "key" in data:
                                key = data["key"].encode("utf-8")
                    except Exception as e:
                        LOGGER.warning("Could not fetch key from mock API, using fallback: %s", e)

                with open(model_path, "rb") as f:
                    encrypted_data = f.read()

                decrypted_data = bytearray(len(encrypted_data))
                key_len = len(key)
                for i in range(len(encrypted_data)):
                    decrypted_data[i] = encrypted_data[i] ^ key[i % key_len]

                self.encrypted_model_buffer = bytes(decrypted_data)
                LOGGER.info("Model '%s' securely decrypted into RAM.", model_path)

                try:
                    import os
                    if hasattr(os, "memfd_create"):
                        fd = os.memfd_create("yolo_model")
                        os.write(fd, self.encrypted_model_buffer)
                        final_model_path = f"/proc/self/fd/{fd}"
                        self.model = YOLO(final_model_path)
                        os.close(fd)
                    else:
                        raise NotImplementedError("memfd_create not available")
                except Exception:
                    import os
                    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pt")
                    try:
                        os.write(tmp_fd, self.encrypted_model_buffer)
                        os.close(tmp_fd)
                        final_model_path = tmp_path
                        self.model = YOLO(final_model_path)
                    finally:
                        try:
                            # Tenta apagar dps do load
                            os.unlink(tmp_path)
                        except OSError:
                            pass

                self.yolo_loaded = True
                self.model.predict(np.zeros((64, 64, 3)), verbose=False)
            except Exception as exc:
                LOGGER.exception("Error securely loading encrypted model: %s", exc)
                return
        else:
            try:
                self.model = YOLO(final_model_path)
                self.yolo_loaded = True
                LOGGER.info("Model '%s' loaded.", final_model_path)
                self.model.predict(np.zeros((64, 64, 3)), verbose=False)
            except Exception as exc:
                LOGGER.exception("Error loading Ultralytics model: %s", exc)

        if self.yolo_loaded:
            try:
                dummy = self.model.predict(np.zeros((256, 256, 3), dtype=np.uint8), verbose=False)
                self.supports_segmentation = bool(dummy and getattr(dummy[0], "masks", None) is not None)
            except Exception:
                self.supports_segmentation = False

        if ENABLE_SAHI and self.yolo_loaded:
            try:
                from sahi import AutoDetectionModel
                LOGGER.info("Carregando SAHI Detection Model envolto no YOLOv8...")
                # Sahi usa o path pra carregar o modelo YOLO interno, se for RAM fd deve funcionar
                self.sahi_model = AutoDetectionModel.from_pretrained(
                    model_type='yolov8',
                    model_path=final_model_path if not os.path.exists(final_model_path) else final_model_path, # fallback to param
                    confidence_threshold=DETECTION_CONF,
                    device="cpu" # For edge devices sem setup
                )
                LOGGER.info("SAHI Model carregado com sucesso!")
            except Exception as e:
                LOGGER.error(f"Erro ao inicializar SAHI, iteraremos sem SAHI: {e}")
                self.sahi_model = None

    def detect(self, frame):
        if not self.yolo_loaded:
            return []

        # SAHI (Slicing Aided Hyper Inference) Route
        if ENABLE_SAHI and self.sahi_model is not None:
            from sahi.predict import get_sliced_prediction
            res = get_sliced_prediction(
                frame,
                self.sahi_model,
                slice_height=256,
                slice_width=256,
                overlap_height_ratio=0.2,
                overlap_width_ratio=0.2
            )
            
            sahi_boxes = []
            detections = []
            for obj in res.object_prediction_list:
                bbox = obj.bbox.to_xyxy()
                conf = obj.score.value
                cid = obj.category.id
                sahi_boxes.append(bbox)
                
                # Sahi devolve masks com Instance Segmentation, porem de forma diferenciada
                mask_area_px = 0.0
                if obj.mask is not None:
                    # Contabilizar boolean mask true pixels
                    mask_area_px = float(np.sum(obj.mask.bool_mask > 0))
                
                detections.append({
                    "box": bbox,
                    "class_id": int(cid),
                    "confidence": float(conf),
                    "track_id": -1, # Tracker será atualizado a seguir
                    "mask_area_px": mask_area_px,
                })
                
            # Atualiza Rastreamento Manual (IoU centroid para SAHI)
            mapped_ids = self.tracker.update(sahi_boxes)
            for i, mapped_id in enumerate(mapped_ids):
                detections[i]["track_id"] = mapped_id
                
            return detections
        
        # Default YOLO route (Nativo, com ByteTrack Embutido, otimizado para velocidade Edge)
        results = self.model.track(
            frame,
            verbose=False,
            persist=True,
            tracker=TRACKER_CONFIG,
            conf=DETECTION_CONF,
            iou=DETECTION_IOU,
            imgsz=INFERENCE_IMGSZ,
        )

        result = results[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []

        xyxy = boxes.xyxy.cpu().numpy().astype(int)
        class_ids = boxes.cls.cpu().numpy().astype(int)
        confidences = boxes.conf.cpu().numpy()
        track_ids = (
            boxes.id.cpu().numpy().astype(int)
            if boxes.id is not None
            else np.full(len(xyxy), -1, dtype=int)
        )
        mask_areas = np.zeros(len(xyxy), dtype=np.float32)
        if getattr(result, "masks", None) is not None and getattr(result.masks, "data", None) is not None:
            try:
                mask_stack = result.masks.data.cpu().numpy()
                for i in range(min(len(mask_stack), len(mask_areas))):
                    mask_areas[i] = float(np.sum(mask_stack[i] > 0.5))
                self.supports_segmentation = True
            except Exception:
                pass

        detections = []
        for i in range(len(xyxy)):
            detections.append(
                {
                    "box": xyxy[i],
                    "class_id": int(class_ids[i]),
                    "confidence": float(confidences[i]),
                    "track_id": int(track_ids[i]),
                    "mask_area_px": float(mask_areas[i]) if i < len(mask_areas) else 0.0,
                }
            )
        return detections
