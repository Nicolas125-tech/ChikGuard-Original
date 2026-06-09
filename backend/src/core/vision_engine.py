"""
ChikGuard VisionEngine v3 - Industrial Edge AI Pipeline
======================================================
High-performance pipeline for poultry monitoring:
- CLAHE pre-processing for lighting resilience.
- SAHI (Slicing Aided Hyper Inference) for small object detection.
- YOLOv10/YOLOv8-Seg for instance segmentation and optimized edge inference.
- ByteTrack for robust multi-object tracking.
- Asynchronous execution and TensorRT/OpenVINO ready.
"""

import cv2
import numpy as np
import time
import threading
import logging
import collections
from typing import List, Dict, Any, Optional
from ultralytics import YOLO

try:
    from src.vision.enhanced_detector import AdvancedTrackerWrapper

    _TRACKER_AVAILABLE = True
except ImportError:
    _TRACKER_AVAILABLE = False

# External dependencies (required in Linux setup)
try:
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction

    _SAHI_AVAILABLE = True
except ImportError:
    _SAHI_AVAILABLE = False

logger = logging.getLogger("chikguard.vision_engine")


class VisionEngine:
    def __init__(
        self,
        model_path: str = "yolov8n-seg.pt",
        imgsz: int = 640,
        conf: float = 0.25,
        use_sahi: bool = True,
        device: str = "cpu",
    ):
        """
        Initializes the industrial vision engine.
        """
        self.device = device
        self.imgsz = imgsz
        self.conf = conf
        self.use_sahi = use_sahi and _SAHI_AVAILABLE

        # 1. Load Model (YOLOv8-seg or YOLOv10)
        # For segmentation + tracking, YOLOv8-seg is still the standard.
        # YOLOv10-N/S can be used if provided.
        if model_path.endswith(".engine") or model_path.endswith(".xml"):
            self.model = YOLO(model_path, task="segment")
        else:
            self.model = YOLO(model_path)

        # Don't call .to() on compiled models
        if not (model_path.endswith(".engine") or model_path.endswith(".xml")):
            self.model.to(self.device)

        # 2. Initialize SAHI if enabled
        if self.use_sahi:
            self.sahi_model = AutoDetectionModel.from_pretrained(
                model_type="ultralytics",
                model_path=model_path,
                confidence_threshold=conf,
                device=device,
            )
            logger.info("SAHI initialized for Sliced Inference.")

        # 3. CLAHE Processor
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        # 4. State Management
        self.last_results = None
        self.frame_count = 0
        self.fps_metrics = collections.deque(maxlen=30)
        self._lock = threading.Lock()

        # Tracker for SAHI
        self.sahi_tracker = (
            AdvancedTrackerWrapper(tracker_type="bytetrack", max_lost=15)
            if _TRACKER_AVAILABLE and self.use_sahi
            else None
        )

        # 5. Async Video Stream Management
        self.cap = None
        self.stream_thread = None
        self.is_running = False
        self.frame_buffer = collections.deque(maxlen=3)  # Small buffer to prevent lag

        logger.info(f"VisionEngine V3 loaded on {device}. SAHI: {self.use_sahi}")

    def start_stream(self, source: str | int) -> bool:
        """Starts the asynchronous video stream."""
        with self._lock:
            if self.is_running:
                logger.warning("Stream is already running.")
                return False

            self.cap = cv2.VideoCapture(source)
            if not self.cap.isOpened():
                logger.error(f"Failed to open video source: {source}")
                return False

            # Prevent frame accumulation to ensure zero-latency streaming
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            self.is_running = True
            self.stream_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.stream_thread.start()
            logger.info(f"Started video stream from source: {source}")
            return True

    def _capture_loop(self):
        """Background daemon thread that continuously reads frames."""
        while self.is_running:
            if self.cap is None or not self.cap.isOpened():
                break

            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Failed to read frame from stream.")
                time.sleep(0.1)  # Prevent tight loop on failure
                continue

            # Put frame in deque (automatically drops oldest if full)
            self.frame_buffer.append(frame)

    def read_frame(self) -> Optional[np.ndarray]:
        """Reads the latest frame from the buffer, preventing lag."""
        try:
            # Pop the most recent frame and clear older ones to maintain chronological sync
            # with tracking algorithms
            frame = self.frame_buffer.pop()
            self.frame_buffer.clear()
            return frame
        except IndexError:
            return None  # Buffer is empty

    def stop_stream(self):
        """Stops the asynchronous video stream."""
        with self._lock:
            self.is_running = False
            if self.stream_thread:
                self.stream_thread.join(timeout=1.0)
            if self.cap:
                self.cap.release()
            self.frame_buffer.clear()
            logger.info("Video stream stopped.")

    def pre_process(self, frame: np.ndarray) -> np.ndarray:
        """
        Applies CLAHE and basic normalization to the frame.
        """
        # Convert to LAB for CLAHE (best for lighting stabilization)
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l2 = self.clahe.apply(l)
        lab = cv2.merge((l2, a, b))
        stabilized = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        return stabilized

    def process_frame(self, frame: np.ndarray, apply_tracking: bool = True) -> Dict[str, Any]:
        """
        Main pipeline execution.
        """
        t0 = time.perf_counter()

        # Instantiate analytics engine on the fly if needed
        analytics_engine = None
        try:
            from src.core.analytics_engine import AnalyticsEngine
            from database import db

            analytics_engine = AnalyticsEngine(db.session, camera_id="stream")
        except ImportError:
            pass

        # A. Pre-processing
        clean_frame = self.pre_process(frame)

        # B. Inference (SAHI vs standard)
        if self.use_sahi:
            # Sliced Inference for Small Objects
            result = get_sliced_prediction(
                clean_frame,
                self.sahi_model,
                slice_height=320,
                slice_width=320,
                overlap_height_ratio=0.2,
                overlap_width_ratio=0.2,
                verbose=0,
            )
            detections = self._format_sahi_output(result)

            # Apply tracking to SAHI detections
            if apply_tracking and self.sahi_tracker:
                boxes = [d["box"] for d in detections]
                confs = [d["confidence"] for d in detections]
                classes = [d["class_id"] for d in detections]
                track_ids = self.sahi_tracker.update(boxes, confs, classes, clean_frame)
                for i, tid in enumerate(track_ids):
                    detections[i]["track_id"] = int(tid)
        else:
            # Standard Instance Segmentation with ByteTrack
            if apply_tracking:
                results = self.model.track(
                    clean_frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    conf=self.conf,
                    imgsz=self.imgsz,
                    verbose=False,
                )
            else:
                results = self.model.predict(
                    clean_frame, conf=self.conf, imgsz=self.imgsz, verbose=False
                )
            detections = self._format_yolo_output(results[0])

        # Generate metrics
        if analytics_engine and detections:
            analytics_engine.export_metrics(detections, t0)

        latency = (time.perf_counter() - t0) * 1000

        return {
            "detections": detections,
            "latency_ms": round(latency, 2),
            "processed_frame": clean_frame if self.use_sahi else None,  # usually shared
        }

    def _format_yolo_output(self, result) -> List[Dict[str, Any]]:
        """Converts Ultralytics Result object to ChikGuard format."""
        formatted = []
        if result.boxes is None:
            return formatted

        # Extract Boxes, Masks, IDs
        boxes = result.boxes.xyxy.cpu().numpy()
        confs = result.boxes.conf.cpu().numpy()
        clss = result.boxes.cls.cpu().numpy()
        ids = result.boxes.id.cpu().numpy() if result.boxes.id is not None else [-1] * len(boxes)

        masks = None
        if result.masks is not None:
            masks = result.masks.data.cpu().numpy()

        for i in range(len(boxes)):
            det = {
                "box": boxes[i].tolist(),
                "confidence": float(confs[i]),
                "class_id": int(clss[i]),
                "track_id": int(ids[i]),
                "mask_area_px": 0.0,
            }
            if masks is not None:
                # Calculate exact area from mask for overlap resolution
                det["mask_area_px"] = float(np.sum(masks[i] > 0.5))

            formatted.append(det)
        return formatted

    def _format_sahi_output(self, sahi_result) -> List[Dict[str, Any]]:
        """Converts SAHI result to ChikGuard format."""
        formatted = []
        for det in sahi_result.object_prediction_list:
            formatted.append(
                {
                    "box": [det.bbox.minx, det.bbox.miny, det.bbox.maxx, det.bbox.maxy],
                    "confidence": float(det.score.value),
                    "class_id": int(det.category.id),
                    "track_id": -1,  # SAHI doesn't track natively between slices
                    "mask_area_px": float(det.mask.area) if det.mask else 0.0,
                }
            )
        return formatted

    def export_for_edge(self, format="tensorrt"):
        """
        Converts the active model to TensorRT or OpenVINO.
        Must be run on the target hardware.
        """
        logger.info(f"Exporting model to {format} format (FP16)...")
        try:
            path = self.model.export(format=format, half=True, opset=12)
            logger.info(f"Model exported successfully: {path}")
            return path
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return None


# Helper globally accessible instance
_engine_instance = None


def get_vision_engine(**kwargs):
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = VisionEngine(**kwargs)
    return _engine_instance
