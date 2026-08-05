import os
import sys
import unittest.mock as mock

import pytest

# Adjust sys.path to see src/ and backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Mock cv2 to avoid errors in app vision module initialization
sys.modules["cv2"] = mock.MagicMock()

# Environment variables setup for Flask tests
os.environ["FLASK_ENV"] = "testing"
os.environ["SUPABASE_JWT_SECRET"] = os.environ.get("SUPABASE_JWT_SECRET", "dummy_secret_dummy_secret_dummy_secret_for_tests_32bytes")
os.environ["ADMIN_PASSWORD"] = "testpassword"
os.environ["ADMIN_EMAIL"] = "test@example.com"
os.environ["JWT_SECRET_KEY"] = "testsecret"
os.environ["CORS_ALLOWED_ORIGINS"] = "*"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from src.audio.respiratory_classifier import RespiratoryDiseaseClassifier

def test_emit_alert_mqtt_failure():
    """Valida que uma falha na publicação MQTT registra um log de erro."""
    classifier = RespiratoryDiseaseClassifier(model_path="dummy.onnx")

    mock_broker = mock.MagicMock()
    mock_broker.publish.side_effect = Exception("Conexão perdida")

    with mock.patch("src.audio.respiratory_classifier.logger") as mock_logger:
        classifier._emit_alert("zona_1", mock_broker)

        mock_broker.publish.assert_called_once()
        mock_logger.error.assert_called_once()
        assert "Falha de I/O ao notificar o Message Broker" in mock_logger.error.call_args[0][0]
