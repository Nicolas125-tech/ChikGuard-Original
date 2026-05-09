import json
import logging
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger("chikguard.analytics_engine")

class AnalyticsEngine:
    def __init__(self, db_session, camera_id: str, export_interval: float = 10.0):
        """
        Initializes the Analytics Engine.
        Requires an active SQLAlchemy db_session to write metrics.
        """
        self.db = db_session
        self.camera_id = camera_id
        self.export_interval = export_interval
        self.last_export_time = datetime.now(timezone.utc).timestamp()

        # Local state to calculate metrics between frames
        self.bird_last_state = {} # dict mapping track_id to { "x": float, "y": float, "ts": float }

        # Buffer to aggregate metrics before export
        self.metrics_buffer = {
            "total_birds": 0,
            "total_mask_area": 0.0,
            "total_velocity": 0.0,
            "active_tracked_birds": 0,
            "frame_count": 0
        }

    def export_metrics(self, detections: List[Dict[str, Any]], frame_timestamp: float) -> Optional[Any]:
        """
        Calculates density and activity metrics from the detections.
        Aggregates them in a buffer and exports to the database periodically.
        Activity is measured in pixels/second based on tracking IDs.
        """
        from database import EventLog # Local import to avoid circular dependency

        if not detections:
            return None

        total_birds = len(detections)
        total_mask_area = sum(d.get("mask_area_px", 0.0) for d in detections)

        # Calculate activity (pixels/second)
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
                        velocity = dist / dt # pixels/second

                        total_velocity += velocity
                        active_tracked_birds += 1

        # Update state for next frame
        self.bird_last_state = current_state

        # Accumulate metrics
        self.metrics_buffer["total_birds"] += total_birds
        self.metrics_buffer["total_mask_area"] += total_mask_area
        self.metrics_buffer["total_velocity"] += total_velocity
        self.metrics_buffer["active_tracked_birds"] += active_tracked_birds
        self.metrics_buffer["frame_count"] += 1

        # Check if it's time to export
        now = datetime.now(timezone.utc).timestamp()
        if (now - self.last_export_time) < self.export_interval:
            return None

        frames = self.metrics_buffer["frame_count"]
        if frames == 0:
            return None

        # Calculate averages over the export interval
        avg_birds = round(self.metrics_buffer["total_birds"] / frames)
        avg_mask_area = self.metrics_buffer["total_mask_area"] / frames

        total_tracked = self.metrics_buffer["active_tracked_birds"]
        avg_activity_px_s = self.metrics_buffer["total_velocity"] / total_tracked if total_tracked > 0 else 0.0
        avg_tracked_ratio = total_tracked / self.metrics_buffer["total_birds"] if self.metrics_buffer["total_birds"] > 0 else 0.0

        # Format payload for EventLog.metadata_json
        payload = {
            "density_birds": avg_birds,
            "density_mask_area_px": avg_mask_area,
            "activity_px_s": round(avg_activity_px_s, 2),
            "tracked_ratio": round(avg_tracked_ratio, 2)
        }

        try:
            # We must use timezone-naive UTC datetime for the timestamp column as per codebase standards
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

            event = EventLog(
                camera_id=self.camera_id,
                event_type="vision_metrics",
                level="info",
                message=f"CV Analytics: ~{avg_birds} birds, {avg_activity_px_s:.1f} px/s avg movement",
                timestamp=now_utc,
                metadata_json=json.dumps(payload)
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
            # Reset buffer and timestamp regardless of DB success to prevent stale accumulation
            self.metrics_buffer = {
                "total_birds": 0,
                "total_mask_area": 0.0,
                "total_velocity": 0.0,
                "active_tracked_birds": 0,
                "frame_count": 0
            }
            self.last_export_time = now
