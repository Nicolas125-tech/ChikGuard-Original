import pytest
import numpy as np
import cv2
from src.vision.tamper_detector import CameraTamperDetector

def test_no_frame():
    detector = CameraTamperDetector()
    result = detector.analyze_frame(None)
    assert result["tamper_detected"] is True
    assert "NO_FRAME" in result["causes"]

    result = detector.analyze_frame(np.array([]))
    assert result["tamper_detected"] is True
    assert "NO_FRAME" in result["causes"]

def test_normal_frame():
    detector = CameraTamperDetector()
    np.random.seed(42)
    frame = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)

    result = detector.analyze_frame(frame)
    assert result["tamper_detected"] is False
    assert len(result["causes"]) == 0
    assert result["is_dark"] is False
    assert result["is_blurred"] is False
    assert result["is_frozen"] is False

def test_dark_frame():
    detector = CameraTamperDetector(min_brightness=15.0)
    frame = np.ones((100, 100, 3), dtype=np.uint8) * 5

    result = detector.analyze_frame(frame)
    assert result["tamper_detected"] is True
    assert "DARK_OR_COVERED" in result["causes"]
    assert result["is_dark"] is True
    assert result["brightness"] < 15.0

def test_blurred_frame():
    detector = CameraTamperDetector(min_laplacian_var=80.0)
    frame = np.ones((100, 100, 3), dtype=np.uint8) * 100

    result = detector.analyze_frame(frame)
    assert result["tamper_detected"] is True
    assert "DEFOCUS_BLUR" in result["causes"]
    assert result["is_blurred"] is True
    assert result["blur_score"] < 80.0

def test_frozen_frame():
    detector = CameraTamperDetector(freeze_frames_threshold=5)
    np.random.seed(42)
    frame = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)

    result = detector.analyze_frame(frame)
    assert result["is_frozen"] is False

    for _ in range(5):
        result = detector.analyze_frame(frame)

    assert result["tamper_detected"] is True
    assert "VIDEO_FREEZE" in result["causes"]
    assert result["is_frozen"] is True

def test_frozen_recovery():
    detector = CameraTamperDetector(freeze_frames_threshold=3)
    np.random.seed(42)
    frame1 = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)
    frame2 = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)

    detector.analyze_frame(frame1)

    for _ in range(3):
        result = detector.analyze_frame(frame1)

    assert result["is_frozen"] is True
    assert result["freeze_counter"] == 3

    result = detector.analyze_frame(frame2)
    assert result["is_frozen"] is False
    assert result["freeze_counter"] == 2

def test_dark_counter_persistence():
    detector = CameraTamperDetector(min_brightness=15.0)
    dark_frame = np.ones((100, 100, 3), dtype=np.uint8) * 5
    normal_frame = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)

    for _ in range(12):
        detector.analyze_frame(dark_frame)

    assert detector._dark_counter == 12

    result = detector.analyze_frame(normal_frame)
    assert "DARK_OR_COVERED" in result["causes"]
    assert result["is_dark"] is False

def test_blur_counter_persistence():
    detector = CameraTamperDetector(min_laplacian_var=80.0)
    blur_frame = np.ones((100, 100, 3), dtype=np.uint8) * 100
    np.random.seed(42)
    normal_frame = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)

    for _ in range(12):
        detector.analyze_frame(blur_frame)

    assert detector._blur_counter == 12

    result = detector.analyze_frame(normal_frame)
    assert "DEFOCUS_BLUR" in result["causes"]
    assert result["is_blurred"] is False
