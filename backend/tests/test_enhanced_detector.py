import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import pytest
from src.domain.vision.enhanced_detector import _box_area, _iou


def test_box_area():
    # Regular box
    box1 = [0, 0, 10, 10]
    assert _box_area(box1) == 100.0

    # Zero width
    box2 = [0, 0, 0, 10]
    assert _box_area(box2) == 0.0

    # Zero height
    box3 = [0, 0, 10, 0]
    assert _box_area(box3) == 0.0

    # Negative dimensions (invalid box represented as inverted coordinates)
    box4 = [10, 10, 0, 0]
    assert _box_area(box4) == 0.0


def test_iou():
    box1 = [0, 0, 10, 10]
    box2 = [0, 0, 10, 10]
    # Identical
    assert _iou(box1, box2) == 1.0

    # Non-overlapping
    box3 = [20, 20, 30, 30]
    assert _iou(box1, box3) == 0.0

    # Partially overlapping
    box4 = [5, 5, 15, 15]
    assert pytest.approx(_iou(box1, box4), 1e-4) == 25 / 175

    # One inside another
    box5 = [2, 2, 8, 8]
    assert pytest.approx(_iou(box1, box5), 1e-4) == 0.36

    # Edge case: One box is zero-area
    box_zero = [0, 0, 0, 10]
    assert _iou(box1, box_zero) == 0.0
    assert _iou(box_zero, box1) == 0.0

    # Edge case: Both boxes are zero-area
    assert _iou(box_zero, box_zero) == 0.0

    # Edge case: Disjoint zero-area boxes
    box_zero_2 = [20, 20, 20, 30]
    assert _iou(box_zero, box_zero_2) == 0.0
