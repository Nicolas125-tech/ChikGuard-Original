import json
import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("chikguard.analytics_engine")


class AnalyticsEngine:
    def __init__(self, db_session, camera_id: str, export_interval: float = 5.0):
        """
        Initializes the Analytics Engine.
        Requires an active SQLAlchemy db_session to write metrics.
        """
        self.db = db_session
        self.camera_id = camera_id
        self.export_interval = export_interval

        # Local state to calculate metrics between frames
        self.bird_last_state = {}  # dict mapping track_id to { "x": float, "y": float, "ts": float }

        import time

        # Buffer to accumulate metrics for aggregated exports
        self.metrics_buffer = {
            "density_birds": [],
            "density_mask_area_px": [],
            "activity_px_s": [],
            "tracked_ratio": [],
        }
        self.last_export_time = time.time()

    def _calculate_metrics(self, detections: List[Dict[str, Any]], frame_timestamp: float) -> tuple:
        total_birds = len(detections)
        total_velocity = 0.0
        active_tracked_birds = 0
        current_state = {}

        for det in detections:
            track_id = det.get("track_id", -1)
            box = det.get("box", [0, 0, 0, 0])

            # Calculate center point
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0

            if track_id != -1:
                current_state[track_id] = {"x": cx, "y": cy, "ts": frame_timestamp}

                # If we saw this bird before, calculate its velocity
                if track_id in self.bird_last_state:
                    prev = self.bird_last_state[track_id]
                    dt = frame_timestamp - prev["ts"]

                    if dt > 0:
                        dx = cx - prev["x"]
                        dy = cy - prev["y"]
                        dist = math.hypot(dx, dy)
                        velocity = dist / dt  # pixels/second

                        total_velocity += velocity
                        active_tracked_birds += 1

        avg_activity_px_s = (
            total_velocity / active_tracked_birds if active_tracked_birds > 0 else 0.0
        )
        tracked_ratio = active_tracked_birds / total_birds if total_birds > 0 else 0.0

        return avg_activity_px_s, tracked_ratio, current_state

    def _buffer_metrics(self, total_birds: int, total_mask_area: float, avg_activity_px_s: float, tracked_ratio: float):
        self.metrics_buffer["density_birds"].append(total_birds)
        self.metrics_buffer["density_mask_area_px"].append(total_mask_area)
        self.metrics_buffer["activity_px_s"].append(avg_activity_px_s)
        self.metrics_buffer["tracked_ratio"].append(tracked_ratio)

    def _export_buffered_metrics_if_ready(self) -> Optional[Any]:
        import time
        from database import EventLog

        current_time = time.time()
        if current_time - self.last_export_time >= self.export_interval:
            try:
                # Calculate averages for the buffered period
                avg_density = sum(self.metrics_buffer["density_birds"]) / len(
                    self.metrics_buffer["density_birds"]
                )
                avg_mask_area = sum(self.metrics_buffer["density_mask_area_px"]) / len(
                    self.metrics_buffer["density_mask_area_px"]
                )
                avg_activity = sum(self.metrics_buffer["activity_px_s"]) / len(
                    self.metrics_buffer["activity_px_s"]
                )
                avg_tracked_ratio = sum(self.metrics_buffer["tracked_ratio"]) / len(
                    self.metrics_buffer["tracked_ratio"]
                )

                # Format payload for EventLog.metadata_json
                payload = {
                    "density_birds": round(avg_density, 2),
                    "density_mask_area_px": round(avg_mask_area, 2),
                    "activity_px_s": round(avg_activity, 2),
                    "tracked_ratio": round(avg_tracked_ratio, 2),
                }

                # We must use timezone-naive UTC datetime for the timestamp column as per codebase standards
                now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

                event = EventLog(
                    camera_id=self.camera_id,
                    event_type="vision_metrics",
                    level="info",
                    message=f"CV Analytics: ~{int(avg_density)} birds, {avg_activity:.1f} px/s avg movement over {self.export_interval}s",
                    timestamp=now_utc,
                    metadata_json=json.dumps(payload),
                )

                self.db.add(event)
                self.db.commit()

                logger.debug(f"Exported aggregated CV metrics to DB for camera {self.camera_id}")
                return event

            except Exception as e:
                self.db.rollback()
                logger.error(f"Failed to export metrics to database: {e}")
                return None
            finally:
                # Always clear the buffer to prevent memory leaks and reset the timer
                self.metrics_buffer = {
                    "density_birds": [],
                    "density_mask_area_px": [],
                    "activity_px_s": [],
                    "tracked_ratio": [],
                }
                self.last_export_time = current_time

        return None

    def export_metrics(
        self, detections: List[Dict[str, Any]], frame_timestamp: float
    ) -> Optional[Any]:
        """
        Calculates density and activity metrics from the detections, buffers them,
        and exports them to the database periodically based on `export_interval`.
        Activity is measured in pixels/second based on tracking IDs.
        """
        if not detections:
            return None

        total_birds = len(detections)
        total_mask_area = sum(d.get("mask_area_px", 0.0) for d in detections)

        avg_activity_px_s, tracked_ratio, current_state = self._calculate_metrics(detections, frame_timestamp)

        # Update state for next frame
        self.bird_last_state = current_state

        self._buffer_metrics(total_birds, total_mask_area, avg_activity_px_s, tracked_ratio)

        return self._export_buffered_metrics_if_ready()
