import os
import sys
import importlib.util
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

# Adjust sys.path to see src/ for PluginBase
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from src.plugins.base import PluginBase

def load_plugin_module():
    """Loads the plugin dynamically exactly how PluginManager does it."""
    plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../plugins/biosafety_audit"))
    plugin_file = os.path.join(plugin_dir, "plugin.py")
    spec = importlib.util.spec_from_file_location("chikguard_plugin_biosafety_audit", plugin_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@pytest.fixture
def mock_yolo():
    with patch("ultralytics.YOLO") as mock:
        yield mock

def test_plugin_metadata(mock_yolo):
    module = load_plugin_module()
    plugin = module.register()
    assert isinstance(plugin, PluginBase)
    assert plugin.info.name == "biosafety_audit"
    assert plugin.info.version == "1.0.0"
    assert "EPI" in plugin.info.description

def test_process_frame_ignored_zones(mock_yolo):
    module = load_plugin_module()
    plugin = module.register()
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = plugin.process_frame(frame, camera_zone="RESTRICTED_GALLERY")
    assert result is None
    mock_yolo.return_value.predict.assert_not_called()

def test_process_frame_person_with_all_epi(mock_yolo):
    module = load_plugin_module()
    plugin = module.register()
    
    mock_results = MagicMock()
    
    boxes_data = [
        [100.0, 100.0, 300.0, 400.0], # person
        [180.0, 100.0, 220.0, 150.0], # helmet
        [150.0, 180.0, 250.0, 300.0], # vest
        [150.0, 350.0, 250.0, 400.0], # boots
    ]
    classes_data = [0, 1, 2, 3]
    confidences_data = [0.9, 0.85, 0.88, 0.82]
    
    mock_boxes = MagicMock()
    mock_boxes.xyxy = np.array(boxes_data)
    mock_boxes.cls = np.array(classes_data)
    mock_boxes.conf = np.array(confidences_data)
    mock_results.boxes = mock_boxes
    
    mock_yolo.return_value.predict.return_value = [mock_results]
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    events = plugin.process_frame(frame, camera_zone="ENTRANCE")
    
    assert len(events) == 0

def test_process_frame_person_missing_helmet(mock_yolo):
    module = load_plugin_module()
    plugin = module.register()
    
    mock_results = MagicMock()
    
    boxes_data = [
        [100.0, 100.0, 300.0, 400.0], # person
        [150.0, 180.0, 250.0, 300.0], # vest
        [150.0, 350.0, 250.0, 400.0], # boots
    ]
    # Class IDs: 0=person, 1=helmet, 2=vest, 3=boots
    classes_data = [0, 2, 3] # Missing helmet (1)
    confidences_data = [0.9, 0.88, 0.82]
    
    mock_boxes = MagicMock()
    mock_boxes.xyxy = np.array(boxes_data)
    mock_boxes.cls = np.array(classes_data)
    mock_boxes.conf = np.array(confidences_data)
    mock_results.boxes = mock_boxes
    
    mock_yolo.return_value.predict.return_value = [mock_results]
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    with patch.object(module, "_log_event") as mock_log:
        events = plugin.process_frame(frame, camera_zone="SANITARY_BARRIER")
        
        assert len(events) == 1
        event = events[0]
        assert event["event_type"] == "EPI_VIOLATION"
        assert event["level"] == "critical"
        assert "helmet" in event["message"]
        mock_log.assert_called_once()

def test_process_frame_vehicle_detection(mock_yolo):
    module = load_plugin_module()
    plugin = module.register()
    
    mock_results = MagicMock()
    
    boxes_data = [
        [50.0, 200.0, 450.0, 450.0], # vehicle
    ]
    classes_data = [6] # vehicle
    confidences_data = [0.95]
    
    mock_boxes = MagicMock()
    mock_boxes.xyxy = np.array(boxes_data)
    mock_boxes.cls = np.array(classes_data)
    mock_boxes.conf = np.array(confidences_data)
    mock_results.boxes = mock_boxes
    
    mock_yolo.return_value.predict.return_value = [mock_results]
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    with patch.object(module, "_log_event") as mock_log:
        events = plugin.process_frame(frame, camera_zone="ENTRANCE")
        
        assert len(events) == 1
        event = events[0]
        assert event["event_type"] == "VEHICLE_DETECTION"
        assert event["level"] == "critical"
        assert "Veículo detectado na entrada" in event["message"]
        mock_log.assert_called_once()
