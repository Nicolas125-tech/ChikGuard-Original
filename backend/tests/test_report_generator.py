import sys

if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.reports.generator import generate_esg_report, generate_weekly_report


def mock_utcnow():
    return datetime(2023, 10, 20, 12, 0, 0)

def test_generate_weekly_report_db_error():
    """Test that a database connection failure raises an exception that can be caught."""
    # Setup mock app context
    mock_app_context = MagicMock()
    mock_context_manager = MagicMock()
    mock_app_context.return_value = mock_context_manager
    mock_context_manager.__enter__.return_value = None

    class MockTimestamp:
        def __ge__(self, other):
            return True
        def __le__(self, other):
            return True

    # Patch the Reading attribute specifically to raise an exception
    with patch("src.reports.generator.Reading") as mock_reading:
        # Prevent the > operator on MagicMock by directly mocking the timestamp property
        mock_reading.timestamp = MockTimestamp()
        mock_reading.query.filter.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception) as exc_info:
            generate_weekly_report(mock_app_context, "cam-01", mock_utcnow)

        assert "Database connection failed" in str(exc_info.value)

def test_generate_esg_report_db_error():
    """Test that a database connection failure raises an exception that can be caught for ESG reports."""
    # Setup mock app context
    mock_app_context = MagicMock()
    mock_context_manager = MagicMock()
    mock_app_context.return_value = mock_context_manager
    mock_context_manager.__enter__.return_value = None

    class MockTimestamp:
        def __ge__(self, other):
            return True
        def __le__(self, other):
            return True

    # Patch the Reading attribute specifically to raise an exception
    with patch("src.reports.generator.Reading") as mock_reading:
        mock_reading.timestamp = MockTimestamp()
        mock_reading.query.filter.side_effect = Exception("Database connection failed for ESG")

        with pytest.raises(Exception) as exc_info:
            generate_esg_report(mock_app_context, "cam-01", mock_utcnow)

        assert "Database connection failed for ESG" in str(exc_info.value)


def test_generate_weekly_report_success():
    mock_app_context = MagicMock()
    mock_app_context.return_value.__enter__.return_value = None

    class MockTimestamp:
        def __ge__(self, other): return True
        def __le__(self, other): return True

    with patch("src.reports.generator.Reading") as mock_reading, \
         patch("src.reports.generator.SensorReading") as mock_sensor, \
         patch("src.reports.generator.EventLog") as mock_event, \
         patch("src.reports.generator.os.makedirs") as mock_makedirs, \
         patch("src.reports.generator.canvas.Canvas") as mock_canvas:

        mock_reading.timestamp = MockTimestamp()
        mock_sensor.timestamp = MockTimestamp()
        mock_event.timestamp = MockTimestamp()

        # Mocking objects to simulate DB rows
        r1 = MagicMock(temperatura=25.0)
        mock_reading.query.filter.return_value.all.return_value = [r1]

        s1 = MagicMock(ammonia_ppm=10.0, humidity_pct=50.0, feed_level_pct=80.0, water_level_pct=90.0)
        mock_sensor.query.filter.return_value.all.return_value = [s1]

        e1 = MagicMock(timestamp=datetime(2023, 10, 20, 10, 0, 0), level="WARN", event_type="TEST", message="Test message")
        mock_event.query.filter.return_value.all.return_value = [e1]

        path = generate_weekly_report(mock_app_context, "cam-01", mock_utcnow)

        assert "weekly_report_cam-01_" in path
        mock_makedirs.assert_called_once()
        mock_canvas.assert_called_once()


def test_generate_weekly_report_no_data():
    mock_app_context = MagicMock()
    mock_app_context.return_value.__enter__.return_value = None

    class MockTimestamp:
        def __ge__(self, other): return True
        def __le__(self, other): return True

    with patch("src.reports.generator.Reading") as mock_reading, \
         patch("src.reports.generator.SensorReading") as mock_sensor, \
         patch("src.reports.generator.EventLog") as mock_event, \
         patch("src.reports.generator.os.makedirs") as mock_makedirs, \
         patch("src.reports.generator.canvas.Canvas") as mock_canvas:

        mock_reading.timestamp = MockTimestamp()
        mock_sensor.timestamp = MockTimestamp()
        mock_event.timestamp = MockTimestamp()

        mock_reading.query.filter.return_value.all.return_value = []
        mock_sensor.query.filter.return_value.all.return_value = []
        mock_event.query.filter.return_value.all.return_value = []

        path = generate_weekly_report(mock_app_context, "cam-01", mock_utcnow)

        assert "weekly_report_cam-01_" in path
        mock_makedirs.assert_called_once()
        mock_canvas.assert_called_once()
