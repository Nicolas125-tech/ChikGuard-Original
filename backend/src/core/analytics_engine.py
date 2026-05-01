import json
import logging
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger("chikguard.analytics_engine")

class AnalyticsEngine:
    def __init__(self, db_session, camera_id: str):
        """
        Initializes the Analytics Engine.
        Requires an active SQLAlchemy db_session to write metrics.
        """
        self.db = db_session
        self.camera_id = camera_id

        # Local state to calculate metrics between frames
        self.bird_last_state = {} # dict mapping track_id to { "x": float, "y": float, "ts": float }

    def export_metrics(self, detections: List[Dict[str, Any]], frame_timestamp: float) -> Optional[Any]:
        """
        Calculates density and activity metrics from the detections and exports them to the database.
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

        avg_activity_px_s = total_velocity / active_tracked_birds if active_tracked_birds > 0 else 0.0

        # Format payload for EventLog.metadata_json
        payload = {
            "density_birds": total_birds,
            "density_mask_area_px": total_mask_area,
            "activity_px_s": round(avg_activity_px_s, 2),
            "tracked_ratio": round(active_tracked_birds / total_birds if total_birds > 0 else 0.0, 2)
        }

        try:
            # We must use timezone-naive UTC datetime for the timestamp column as per codebase standards
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

            event = EventLog(
                camera_id=self.camera_id,
                event_type="vision_metrics",
                level="info",
                message=f"CV Analytics: {total_birds} birds, {avg_activity_px_s:.1f} px/s avg movement",
                timestamp=now_utc,
                metadata_json=json.dumps(payload)
            )

            self.db.add(event)
            self.db.commit()

            logger.debug(f"Exported CV metrics to DB for camera {self.camera_id}")
            return event

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to export metrics to database: {e}")
            return None
