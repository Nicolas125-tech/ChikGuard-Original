import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import pytest
import unittest.mock as mock
from flask import Flask, request

from src.api.sensors_api import handle_get_sensors_history, handle_acoustic_classify, create_sensors_blueprint

@pytest.fixture
def app():
    app = Flask(__name__)
    return app

def test_handle_get_sensors_history(app):
    mock_sensor_reading = mock.MagicMock()
    mock_query = mock.MagicMock()
    mock_sensor_reading.query = mock_query

    mock_filter = mock.MagicMock()
    mock_order = mock.MagicMock()
    mock_limit = mock.MagicMock()

    mock_query.filter_by.return_value = mock_filter
    mock_filter.order_by.return_value = mock_order
    mock_order.limit.return_value = mock_limit

    mock_sensor_reading.id.desc.return_value = "desc_id"

    mock_row1 = mock.MagicMock()
    mock_row1.to_dict.return_value = {"id": 2, "temperature_c": 26.0}
    mock_row2 = mock.MagicMock()
    mock_row2.to_dict.return_value = {"id": 1, "temperature_c": 25.0}

    mock_limit.all.return_value = [mock_row1, mock_row2]

    deps = {
        "active_camera_id": "cam-1",
        "SensorReading": mock_sensor_reading
    }

    with app.test_request_context('/?limit=10'):
        request.tenant_id = 1
        response = handle_get_sensors_history(deps)

        assert response.status_code == 200
        data = response.json
        assert data["count"] == 2

        # Should be reversed in the response (descending order in db -> reversed in UI)
        assert data["items"][0]["id"] == 1
        assert data["items"][1]["id"] == 2

        mock_query.filter_by.assert_called_once_with(tenant_id=1, camera_id="cam-1")
        mock_filter.order_by.assert_called_once_with("desc_id")
        mock_order.limit.assert_called_once_with(10)

def test_handle_get_sensors_history_limit_clamping(app):
    mock_sensor_reading = mock.MagicMock()
    mock_query = mock.MagicMock()
    mock_sensor_reading.query = mock_query

    mock_filter = mock.MagicMock()
    mock_order = mock.MagicMock()
    mock_limit = mock.MagicMock()

    mock_query.filter_by.return_value = mock_filter
    mock_filter.order_by.return_value = mock_order
    mock_order.limit.return_value = mock_limit

    mock_limit.all.return_value = []

    deps = {
        "active_camera_id": "cam-1",
        "SensorReading": mock_sensor_reading
    }

    # Test limit over maximum
    with app.test_request_context('/?limit=6000'):
        request.tenant_id = 1
        handle_get_sensors_history(deps)
        mock_order.limit.assert_called_with(5000)

    # Test limit under minimum
    with app.test_request_context('/?limit=0'):
        request.tenant_id = 1
        handle_get_sensors_history(deps)
        mock_order.limit.assert_called_with(1)


def test_handle_acoustic_classify_model_not_loaded(app):
    mock_classifier = mock.MagicMock()
    mock_classifier.loaded = False
    mock_classifier.last_error = "Model file not found"

    deps = {
        "audio_classifier": mock_classifier,
        "sf": mock.MagicMock()
    }

    with app.test_request_context('/api/acoustic/classify', method='POST'):
        response, status_code = handle_acoustic_classify(deps)
        assert status_code == 400
        assert response.json["msg"] == "Modelo de tosse nao carregado"
        assert response.json["model_error"] == "Model file not found"


def test_handle_acoustic_classify_sf_missing(app):
    mock_classifier = mock.MagicMock()
    mock_classifier.loaded = True

    deps = {
        "audio_classifier": mock_classifier,
        "sf": None
    }

    with app.test_request_context('/api/acoustic/classify', method='POST'):
        response, status_code = handle_acoustic_classify(deps)
        assert status_code == 500
        assert response.json["msg"] == "Dependencia soundfile nao disponivel no backend"


def test_handle_acoustic_classify_no_audio_file(app):
    mock_classifier = mock.MagicMock()
    mock_classifier.loaded = True

    deps = {
        "audio_classifier": mock_classifier,
        "sf": mock.MagicMock()
    }

    with app.test_request_context('/api/acoustic/classify', method='POST'):
        response, status_code = handle_acoustic_classify(deps)
        assert status_code == 400
        assert response.json["msg"] == "Envie arquivo de audio no campo 'audio'"


def test_handle_acoustic_classify_success(app):
    import io
    import numpy as np

    mock_classifier = mock.MagicMock()
    mock_classifier.loaded = True
    mock_classifier.classify.return_value = {
        "respiratory_health_index": 85.0,
        "cough_index": 70.0,
        "stress_audio_index": 15.0,
    }

    mock_sf = mock.MagicMock()
    mock_sf.read.return_value = (np.array([0.1, 0.2]), 16000)

    mock_db = mock.MagicMock()
    mock_enqueue = mock.MagicMock()
    mock_log_event = mock.MagicMock()
    mock_audit = mock.MagicMock()
    mock_reading_cls = mock.MagicMock()

    acoustic_state = {}

    deps = {
        "audio_classifier": mock_classifier,
        "sf": mock_sf,
        "io": io,
        "np": np,
        "acoustic_state": acoustic_state,
        "AcousticReading": mock_reading_cls,
        "active_camera_id": "cam-1",
        "db": mock_db,
        "enqueue_sync_item": mock_enqueue,
        "log_event": mock_log_event,
        "audit": mock_audit,
    }

    audio_data = io.BytesIO(b"fake audio data")

    with app.test_request_context(
        '/api/acoustic/classify',
        method='POST',
        data={'audio': (audio_data, 'test.wav')}
    ):
        request.tenant_id = 1
        response = handle_acoustic_classify(deps)

        assert response.status_code == 200
        data = response.json
        assert data["msg"] == "Audio classificado com sucesso"
        assert acoustic_state["cough_index"] == 70.0
        assert mock_db.session.commit.called
        assert mock_log_event.called
        assert mock_audit.called
