import time
import os
import sqlite3
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Try to import app components directly to run the function
try:
    from backend.app_flask_legacy import app, db, Reading, BirdSnapshot, BirdTrackPoint, EventLog, SensorReading, ThermalAnomaly, AcousticReading, _process_data_lifecycle
    has_app = True
except Exception as e:
    print(f"Failed to import app: {e}")
    has_app = False

print(f"Can test: {has_app}")
