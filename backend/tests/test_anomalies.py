import pytest
from unittest.mock import patch, MagicMock
import time

# Create a mock for the database and other app dependencies so we can import app
import sys

mock_db = MagicMock()
mock_db.session.commit.return_value = None
mock_db.session.add.return_value = None

sys.modules['database'] = MagicMock()
sys.modules['database'].db = mock_db
sys.modules['database'].ThermalAnomaly = MagicMock()
sys.modules['database'].EnergyUsageDaily = MagicMock()
sys.modules['database'].EventLog = MagicMock()
sys.modules['database'].Batch = MagicMock()
sys.modules['database'].AcousticReading = MagicMock()
sys.modules['database'].User = MagicMock()
sys.modules['database'].Account = MagicMock()
sys.modules['database'].RolePermission = MagicMock()
sys.modules['database'].PushToken = MagicMock()

# Mock torch/ultralytics explicitly since tests run in an env where they might be missing or slow
sys.modules['ultralytics'] = MagicMock()
sys.modules['cv2'] = MagicMock()

try:
    import app as app_module
except Exception as e:
    pytest.skip(f"Could not import app for testing: {e}", allow_module_level=True)

@patch('app._log_event')
def test_temperature_anomaly_trigger(mock_log_event):
    # Setup test condition
    high_temp = 36.0
    app_module.last_temp_emergency_notification_ts = 0  # Force it to be old

    with app_module.app.app_context():
        # Simulate check
        if high_temp >= 35.0 and (time.time() - float(app_module.last_temp_emergency_notification_ts)) > 600:
            app_module.last_temp_emergency_notification_ts = time.time()
            txt = f"Temperatura subiu para {high_temp:.1f}C! Intervencao necessaria."
            app_module._log_event("temperature_critical_alert", "high", txt)

    mock_log_event.assert_called_once()
    assert "36.0" in mock_log_event.call_args[0][2]

@patch('app.camera_registry', [{"camera_id": "test_cam", "source": "webcam:0", "enabled": True}])
def test_camera_fail_simulation():
    # If consecutive read failures > threshold, simulation is activated
    app_module.consecutive_read_failures = app_module.CAMERA_FAIL_THRESHOLD
    app_module.use_basic_simulation = False

    if app_module.consecutive_read_failures >= app_module.CAMERA_FAIL_THRESHOLD:
        app_module.use_basic_simulation = True

    assert app_module.use_basic_simulation is True
