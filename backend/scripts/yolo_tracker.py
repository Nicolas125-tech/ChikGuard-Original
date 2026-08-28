import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime

import cv2
import numpy as np
from ultralytics import YOLO

from src.db.nosql_session import MongoDBBatchWriter


class PoultryTracker:
    def __init__(self, model_path, tracker_type="bytetrack.yaml", max_missing_frames=10):
        self.model = YOLO(model_path)
        self.tracker_type = tracker_type
        # Stores history of centroids: {track_id: deque([(x, y, frame_idx), ...])}
        self.track_history = defaultdict(lambda: deque(maxlen=30))
        # Stores last seen frame for interpolation logic
        self.last_seen = {}
        self.max_missing_frames = max_missing_frames
        self.logs = []

        # MongoDB batch writers for high-throughput tracking persistence
        self._mongo_detections = MongoDBBatchWriter(
            "cv_detections", batch_size=100, flush_interval_sec=10.0
        )
        self._mongo_tracks = MongoDBBatchWriter(
            "cv_track_points", batch_size=200, flush_interval_sec=10.0
        )

    def smooth_trajectory(self, track_id, current_centroid, frame_idx):
        """
        Applies basic smoothing and handles temporary occlusions.
        If an object was missing for a few frames, we could interpolate its path.
        For simplicity, we use a moving average on the history.
        """
        history = self.track_history[track_id]

        # If the object was missing, we could theoretically interpolate
        # between last seen and current. Here we just append.
        history.append((*current_centroid, frame_idx))
        self.last_seen[track_id] = frame_idx

        # Calculate smoothed centroid (moving average of last 5 points)
        if len(history) >= 5:
            recent_pts = list(history)[-5:]
            smooth_x = int(np.mean([pt[0] for pt in recent_pts]))
            smooth_y = int(np.mean([pt[1] for pt in recent_pts]))
            return (smooth_x, smooth_y)

        return current_centroid

    def process_video(self, video_path, output_video_path=None, log_file="tracking_logs.json"):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error opening video {video_path}")
            return

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        writer = None
        if output_video_path:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

        frame_idx = 0

        print("Starting tracking...")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1

            # Run YOLO tracking (persist tracks across frames)
            results = self.model.track(
                frame, persist=True, tracker=self.tracker_type, verbose=False
            )

            frame_log = {"timestamp": time.time(), "frame": frame_idx, "detections": []}

            if results[0].boxes is not None and results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                track_ids = results[0].boxes.id.int().cpu().numpy()
                confs = results[0].boxes.conf.cpu().numpy()
                classes = results[0].boxes.cls.cpu().numpy()

                for box, track_id, conf, cls in zip(boxes, track_ids, confs, classes):
                    x1, y1, x2, y2 = map(int, box)
                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)

                    # Apply trajectory smoothing
                    smooth_cx, smooth_cy = self.smooth_trajectory(track_id, (cx, cy), frame_idx)

                    frame_log["detections"].append(
                        {
                            "id": int(track_id),
                            "class": int(cls),
                            "confidence": float(conf),
                            "bbox": [x1, y1, x2, y2],
                            "centroid": [cx, cy],
                            "smoothed_centroid": [smooth_cx, smooth_cy],
                        }
                    )

                    # ── MongoDB: persist detection + trajectory to NoSQL ──
                    now_iso = datetime.utcnow().isoformat()
                    self._mongo_detections.add({
                        "camera_id": "offline_tracker",
                        "track_id": int(track_id),
                        "box": [x1, y1, x2, y2],
                        "confidence": float(conf),
                        "class_id": int(cls),
                        "frame_idx": frame_idx,
                        "timestamp": now_iso,
                    })
                    self._mongo_tracks.add({
                        "camera_id": "offline_tracker",
                        "track_id": int(track_id),
                        "x": smooth_cx,
                        "y": smooth_cy,
                        "frame_idx": frame_idx,
                        "timestamp": now_iso,
                    })

                    # Draw on frame
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        f"ID: {track_id}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2,
                    )

                    # Draw smoothed trajectory
                    hist = list(self.track_history[track_id])
                    for i in range(1, len(hist)):
                        pt1 = (hist[i - 1][0], hist[i - 1][1])
                        pt2 = (hist[i][0], hist[i][1])
                        cv2.line(frame, pt1, pt2, (255, 0, 0), 2)

            self.logs.append(frame_log)

            if writer:
                writer.write(frame)

            # Optional: Display frame (comment out for headless edge processing)
            # cv2.imshow("Tracking", frame)
            # if cv2.waitKey(1) & 0xFF == ord("q"):
            #     break

        cap.release()
        if writer:
            writer.release()
        cv2.destroyAllWindows()

        # Flush remaining MongoDB buffers
        self._mongo_detections.flush_sync()
        self._mongo_tracks.flush_sync()

        # Save logs
        with open(log_file, "w") as f:
            json.dump(self.logs, f, indent=4)

        print(f"Tracking complete. Logs saved to {log_file}")


if __name__ == "__main__":
    MODEL = "yolov8n.pt"  # Update with trained custom model
    VIDEO = "video_granja.mp4"
    OUTPUT_VID = "tracked_output.mp4"

    if os.path.exists(VIDEO):
        tracker = PoultryTracker(model_path=MODEL, tracker_type="bytetrack.yaml")
        tracker.process_video(VIDEO, output_video_path=OUTPUT_VID)
    else:
        print(f"Video {VIDEO} not found.")
