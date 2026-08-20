import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import os
import sys
import unittest.mock as mock

import pytest

# Ajusta sys.path para enxergar src/ e o backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Mock do cv2 para evitar erros na inicialização de módulos de visão do app
sys.modules["cv2"] = mock.MagicMock()

from src.core.multi_camera import MultiCameraOrchestrator


@pytest.fixture
def mock_camera_capture():
    with mock.patch("src.core.multi_camera.CameraCapture") as MockCaptureClass:
        # Mock do objeto CameraCapture retornado pelo construtor
        mock_instance = mock.MagicMock()
        mock_instance.is_live = False
        MockCaptureClass.return_value = mock_instance
        yield MockCaptureClass, mock_instance


def test_multicamera_orchestrator_add_and_list(mock_camera_capture):
    MockClass, mock_inst = mock_camera_capture
    orchestrator = MultiCameraOrchestrator()

    # Adiciona duas câmeras
    success1 = orchestrator.add_stream(camera_id="galpao-1", source="rtsp://192.168.1.50/stream")
    success2 = orchestrator.add_stream(camera_id="galpao-2", source="video_teste.mp4")

    assert success1 is True
    assert success2 is True
    assert MockClass.call_count == 2
    assert mock_inst.start.call_count == 2

    # Lista câmeras ativas
    active_streams = orchestrator.list_active_streams()
    assert "galpao-1" in active_streams
    assert "galpao-2" in active_streams
    assert len(active_streams) == 2


def test_multicamera_orchestrator_duplicate_stream(mock_camera_capture):
    MockClass, mock_inst = mock_camera_capture
    orchestrator = MultiCameraOrchestrator()

    success1 = orchestrator.add_stream(camera_id="galpao-1", source="camera1")
    success2 = orchestrator.add_stream(camera_id="galpao-1", source="camera2")  # ID Duplicado

    assert success1 is True
    assert success2 is False
    assert len(orchestrator.list_active_streams()) == 1


def test_multicamera_orchestrator_remove_stream(mock_camera_capture):
    MockClass, mock_inst = mock_camera_capture
    orchestrator = MultiCameraOrchestrator()

    orchestrator.add_stream(camera_id="galpao-1", source="camera1")

    # Remove fluxo
    removed = orchestrator.remove_stream("galpao-1")
    assert removed is True
    assert mock_inst.stop.call_count == 1
    assert len(orchestrator.list_active_streams()) == 0


def test_multicamera_orchestrator_stop_all(mock_camera_capture):
    MockClass, mock_inst = mock_camera_capture
    orchestrator = MultiCameraOrchestrator()

    orchestrator.add_stream(camera_id="galpao-1", source="camera1")
    orchestrator.add_stream(camera_id="galpao-2", source="camera2")

    orchestrator.stop_all()
    assert mock_inst.stop.call_count == 2
    assert len(orchestrator.list_active_streams()) == 0
