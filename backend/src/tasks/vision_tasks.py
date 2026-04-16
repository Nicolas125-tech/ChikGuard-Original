import cv2
import numpy as np
import base64
import logging
import os
import time
from src.core.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name='src.tasks.vision_tasks.process_active_learning_task')
def process_active_learning_task(frame_b64, detection, conf):
    try:
        from src.mlops.active_learning import active_learning_pipeline
        # Decode frame
        frame_bytes = base64.b64decode(frame_b64)
        np_arr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        active_learning_pipeline._save_uncertain_frame(frame, detection, conf)
        logger.info(f"Celery: Processed active learning frame, conf={conf}")
        return True
    except Exception as e:
        logger.error(f"Celery active learning task failed: {e}")
        return False

@celery_app.task(name='src.tasks.vision_tasks.sync_mlops_data_task')
def sync_mlops_data_task():
    try:
        from src.mlops.active_learning import active_learning_pipeline
        active_learning_pipeline.sync_to_cloud()
        logger.info("Celery: Nightly MLOps sync completed.")
        return True
    except Exception as e:
        logger.error(f"Celery sync task failed: {e}")
        return False
