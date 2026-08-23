import pytest
import numpy as np
from unittest.mock import MagicMock, patch
import app_flask_legacy

def test_draw_overlays_yolo_not_loaded():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    draw_frame = frame.copy()
    with patch.object(app_flask_legacy.detector, 'yolo_loaded', False):
        res = app_flask_legacy._draw_overlays(draw_frame, frame, [], None)
        assert np.array_equal(res, draw_frame)

def test_draw_overlays_legacy_fallback():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    draw_frame = frame.copy()
    selected = [{"box": [10, 10, 50, 50], "class_id": 0, "confidence": 0.9, "track_id": 1}]
    with patch.object(app_flask_legacy.detector, 'yolo_loaded', True), \
         patch.object(app_flask_legacy, '_CV_ENGINE_AVAILABLE', False):
        res = app_flask_legacy._draw_overlays(draw_frame, frame, selected, None)
        assert res is not None

def test_enrich_detections():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    selected = [{"box": [10, 10, 50, 50], "class_id": 0, "mask_area_px": 100.0, "stable_bird_uid": 42}]
    mock_classifier = MagicMock()
    mock_classifier.classify.return_value = {"species": "chicken"}
    mock_analyzer = MagicMock()
    mock_analyzer.analyze.return_value = {"pose": "standing"}

    with patch.object(app_flask_legacy, '_species_classifier', mock_classifier), \
         patch.object(app_flask_legacy, '_pose_analyzer', mock_analyzer):
        app_flask_legacy._enrich_detections(frame, selected)
        assert selected[0]["species"] == "chicken"
        assert selected[0]["pose"] == "standing"
        assert selected[0]["track_id"] == 42
