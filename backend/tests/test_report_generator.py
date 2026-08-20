import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.reports.generator import generate_esg_report, generate_weekly_report


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
